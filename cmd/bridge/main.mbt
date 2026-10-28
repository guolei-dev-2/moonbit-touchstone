///|
extern "js" fn fail_string(message : String) -> String =
  #| (message) => { throw new Error(message); }

///|
fn object(text : String) -> Map[String, Json] raise {
  if text.length() > 1000000 {
    raise Failure("options exceed one million characters")
  }
  match @json.parse(text) {
    Object(o) => o
    _ => raise Failure("options must be an object")
  }
}

///|
fn[T : @json.FromJson] required(o : Map[String, Json], key : String) -> T raise {
  match o.get(key) {
    Some(j) => @json.from_json(j)
    None => raise Failure("missing option: " + key)
  }
}

///|
fn[T : @json.FromJson] optional(
  o : Map[String, Json],
  key : String,
  fallback : T,
) -> T raise {
  match o.get(key) {
    Some(j) => @json.from_json(j)
    None => fallback
  }
}

///|
fn read_document(
  text : String,
  o : Map[String, Json],
  key : String,
) -> @lib.Document raise {
  match o.get(key) {
    Some(j) => @lib.parse(text, ports=integer(j, key))
    None => @lib.parse(text)
  }
}

///|
// Core FromJson[Int] truncates fractions; CLI indices/budgets must not do so.
fn integer(value : Json, key : String) -> Int raise {
  let n : Double = @json.from_json(value)
  if n.is_nan() ||
    n.is_inf() ||
    n.floor() != n ||
    n < -2147483648.0 ||
    n > 2147483647.0 {
    raise Failure(key + " must be an exact Int32 integer")
  }
  n.to_int()
}

///|
fn required_int(o : Map[String, Json], key : String) -> Int raise {
  integer(required(o, key), key)
}

///|
fn optional_int(
  o : Map[String, Json],
  key : String,
  fallback : Int,
) -> Int raise {
  match o.get(key) {
    Some(j) => integer(j, key)
    None => fallback
  }
}

///|
fn bound(o : Map[String, Json], key : String) -> Double? raise {
  match o.get(key) {
    Some(j) => Some(@json.from_json(j))
    None => None
  }
}

///|
fn band_report(
  net : @lib.Network,
  options : Map[String, Json],
) -> @lib.BandReport raise {
  for key in options.keys() {
    if !(key == "command" ||
      key == "ports" ||
      key == "limits" ||
      key == "max_details") {
      raise Failure("unknown band check option: " + key)
    }
  }
  let items : Array[Json] = required(options, "limits")
  if items.is_empty() || items.length() > 256 {
    raise Failure("band check requires 1..256 rules")
  }
  let limits = items.map(item => {
    let o = match item {
      Object(o) => o
      _ => raise Failure("each band rule must be an object")
    }
    // A misspelled bound must not silently disable a requested check.
    for key in o.keys() {
      if !(key == "metric" ||
        key == "start_hz" ||
        key == "end_hz" ||
        key == "input" ||
        key == "output" ||
        key == "minimum" ||
        key == "maximum") {
        raise Failure("unknown band rule option: " + key)
      }
    }
    let name : String = required(o, "metric")
    let metric : @lib.BandMetric = match name {
      "reflection_magnitude" => ReflectionMagnitude
      "transmission_magnitude" => TransmissionMagnitude
      "return_loss_db" => ReturnLossDb
      "insertion_loss_db" => InsertionLossDb
      "vswr" => Vswr
      _ => raise Failure("unknown band metric: " + name)
    }
    @lib.band_limit(
      metric,
      required(o, "start_hz"),
      required(o, "end_hz"),
      input=required_int(o, "input"),
      output=required_int(o, "output"),
      minimum?=bound(o, "minimum"),
      maximum?=bound(o, "maximum"),
    )
  })
  net.check_bands(limits, max_details=optional_int(options, "max_details", 256))
}

///|
// Parsing, validation, transformations, metrics and serialization are MoonBit.
// The Node host only reads/writes files, supplies filename hints and arguments.
fn net_json(net : @lib.Network) -> Json raise {
  {
    "ports": net.ports().to_json(),
    "parameter": net.parameter().to_json(),
    "frequency_hz": net.frequency_hz().to_json(),
    "reference_ohms": net.reference_ohms().to_json(),
    "values": Array::makei(net.frequency_hz().length(), i => net.matrix(i)).to_json(),
  }
}

///|
fn complex_option(o : Map[String, Json], key : String) -> @lib.Complex raise {
  let v : Array[Double] = required(o, key)
  if v.length() != 2 {
    raise Failure("expected [real,imag] for " + key)
  }
  @lib.complex(v[0], im=v[1])
}

///|
fn gain_receipt_object(value : Json, label : String) -> Map[String, Json] raise {
  match value {
    Object(fields) => fields
    _ => raise Failure(label + " must be an object")
  }
}

///|
fn gain_receipt_keys(
  fields : Map[String, Json],
  allowed : Array[String],
  label : String,
) -> Unit raise {
  for key in fields.keys() {
    if !allowed.contains(key) {
      raise Failure("unknown " + label + " field: " + key)
    }
  }
}

///|
fn gain_receipt_schema() -> String {
  "touchstone.gain-receipt.v1"
}

///|
fn gain_receipt_digest(value : String) -> String raise {
  let digest = value.to_lower()
  if digest.length() != 64 ||
    !digest.iter().all(c => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
    raise Failure("receipt SHA256 must contain 64 hexadecimal digits")
  }
  digest
}

///|
fn gain_receipt_size(value : Int) -> Int raise {
  if value < 0 || value > 64000000 {
    raise Failure("receipt input bytes outside 0..64000000")
  }
  value
}

///|
fn gain_receipt_status(result : Map[String, Json]) -> String raise {
  let status : String = required(result, "status")
  if !(status == "pass" || status == "fail" || status == "inconclusive") {
    raise Failure("invalid recorded gain analysis status")
  }
  status
}

///|
fn gain_receipt_request(value : Json) -> Map[String, Json] raise {
  let request = gain_receipt_object(value, "receipt request")
  let command : String = required(request, "command")
  if command != "gain-check" {
    raise Failure("receipt may replay only gain-check")
  }
  request
}

///|
fn gain_record(text : String, o : Map[String, Json]) -> Json raise {
  gain_receipt_keys(
    o,
    ["command", "request", "actual_input_sha256", "actual_input_bytes"],
    "gain-record transport",
  )
  let digest = gain_receipt_digest(required(o, "actual_input_sha256"))
  let bytes = gain_receipt_size(required_int(o, "actual_input_bytes"))
  if bytes != text.length() {
    raise Failure("host byte count does not match ASCII input length")
  }
  let requested : Json = required(o, "request")
  let request = gain_receipt_request(requested)
  let result = @json.parse(execute(text, requested.stringify(), "", ""))
  let result_fields = gain_receipt_object(result, "gain result")
  ignore(gain_receipt_status(result_fields))
  let report = gain_receipt_object(
    required(result_fields, "report"),
    "gain report",
  )
  let matching = gain_receipt_object(
    required(result_fields, "matching"),
    "gain matching",
  )
  let effective : Map[String, Json] = Map([
    ("command", "gain-check".to_json()),
    ("terminal_mode", required(result_fields, "terminal_mode")),
    ("start_hz", required(report, "start_hz")),
    ("end_hz", required(report, "end_hz")),
  ])
  for key in matching.keys() {
    effective[key] = matching.get(key).unwrap()
  }
  for key in ["minimum_db", "maximum_db"] {
    if report.get(key) is Some(value) {
      effective[key] = value
    }
  }
  if request.get("ports") is Some(value) {
    effective["ports"] = integer(value, "ports").to_json()
  }
  {
    "schema": gain_receipt_schema().to_json(),
    "input": { "sha256": digest.to_json(), "bytes": bytes.to_json() },
    "request": effective.to_json(),
    "result": result,
  }
}

///|
fn gain_review(text : String, o : Map[String, Json]) -> Json raise {
  gain_receipt_keys(
    o,
    ["command", "saved", "actual_input_sha256", "actual_input_bytes"],
    "gain-review transport",
  )
  let actual_hash = gain_receipt_digest(required(o, "actual_input_sha256"))
  let actual_bytes = gain_receipt_size(required_int(o, "actual_input_bytes"))
  if actual_bytes != text.length() {
    raise Failure("host byte count does not match ASCII input length")
  }
  let saved = gain_receipt_object(required(o, "saved"), "receipt")
  if !saved.contains("schema") && saved.contains("report") {
    raise Failure(
      "plain gain-check report has no input identity; regenerate with gain-record",
    )
  }
  gain_receipt_keys(saved, ["schema", "input", "request", "result"], "receipt")
  let schema : String = required(saved, "schema")
  if schema != gain_receipt_schema() {
    raise Failure("unsupported gain receipt schema")
  }
  let input = gain_receipt_object(required(saved, "input"), "receipt input")
  gain_receipt_keys(input, ["sha256", "bytes"], "receipt input")
  let expected_hash = gain_receipt_digest(required(input, "sha256"))
  let expected_bytes = gain_receipt_size(required_int(input, "bytes"))
  let requested : Json = required(saved, "request")
  ignore(gain_receipt_request(requested))
  let recorded : Json = required(saved, "result")
  let recorded_fields = gain_receipt_object(recorded, "recorded gain result")
  let recorded_status = gain_receipt_status(recorded_fields)
  let identities : Json = {
    "recorded": {
      "sha256": expected_hash.to_json(),
      "bytes": expected_bytes.to_json(),
    },
    "actual": {
      "sha256": actual_hash.to_json(),
      "bytes": actual_bytes.to_json(),
    },
  }
  if expected_hash != actual_hash || expected_bytes != actual_bytes {
    return {
      "kind": "gain_receipt_replay",
      "status": "input_mismatch",
      "input_match": false,
      "result_match": null,
      "recorded_status": recorded_status.to_json(),
      "current_status": null,
      "input": identities,
      "changed_sections": [],
      "current_result": null,
    }
  }
  let current = @json.parse(execute(text, requested.stringify(), "", ""))
  let current_fields = gain_receipt_object(current, "current gain result")
  let current_status = gain_receipt_status(current_fields)
  let changed : Array[String] = []
  for key in current_fields.keys() {
    if current_fields.get(key) != recorded_fields.get(key) {
      changed.push(key)
    }
  }
  for key in recorded_fields.keys() {
    if !current_fields.contains(key) {
      changed.push(key)
    }
  }
  let same = recorded == current
  {
    "kind": "gain_receipt_replay",
    "status": (if same { "reproduced" } else { "result_mismatch" }).to_json(),
    "input_match": true,
    "result_match": same.to_json(),
    "recorded_status": recorded_status.to_json(),
    "current_status": current_status.to_json(),
    "input": identities,
    "changed_sections": changed.to_json(),
    "current_result": current,
  }
}

///|
fn execute(
  text : String,
  options : String,
  left : String,
  right : String,
) -> String raise {
  let o = object(options)
  let command : String = optional(o, "command", "inspect")
  // Receipt identity must be checked before parsing a different/corrupt model.
  if command == "gain-record" {
    return gain_record(text, o).stringify()
  }
  if command == "gain-review" {
    return gain_review(text, o).stringify()
  }
  let doc = read_document(text, o, "ports")
  let raw = doc.raw_network()
  let result : Json = match command {
    "rf-convert" =>
      net_json(doc.network_only().convert(required(o, "parameter")))
    "single" => net_json(doc.single_ended_network())
    "modal" => net_json(doc.modal_network())
    "mixed" => {
      if !doc.noise_data().is_empty() {
        raise Failure(
          "mixed-mode file conversion cannot encode two-port noise parameters; use an explicit Network analysis view",
        )
      }
      let pairs : Array[Array[Int]] = required(o, "pairs")
      let mixed = doc
        .network_only()
        .to_mixed_mode(
          pairs.map(p => {
            if p.length() != 2 {
              raise Failure("expected differential pair")
            }
            (p[0], p[1])
          }),
        )
      {
        "text": @lib.document(
          mixed.raw_network(),
          noise_reference_ohms=mixed.noise_reference_ohms(),
          mixed_mode_order=mixed.mixed_mode_order(),
          information=doc.information_lines(),
        )
        .write()
        .to_json(),
        "network": net_json(mixed.modal_network()),
        "order": mixed.mixed_mode_order().to_json(),
      }
    }
    "modal-metrics" =>
      doc
      .mixed_mode_metrics(
        required_int(o, "output_pair"),
        required_int(o, "input_pair"),
        cmrr=optional(o, "cmrr", "balanced"),
      )
      .to_json()
    "terminate" => {
      let entries : Array[Array[Double]] = required(o, "terminations")
      let ts = entries.map(v => {
        if v.length() != 3 {
          raise Failure("termination must be [port,re,im]")
        }
        (integer(v[0].to_json(), "port"), @lib.complex(v[1], im=v[2]))
      })
      net_json(
        doc
        .network_only()
        .terminate_ports(ts, impedance=optional(o, "impedance", false)),
      )
    }
    "terminate-file" => {
      for key in o.keys() {
        if !(key == "command" ||
          key == "ports" ||
          key == "terminations" ||
          key == "impedance") {
          raise Failure("unknown terminate-file option: " + key)
        }
      }
      if !doc.noise_data().is_empty() {
        raise Failure(
          "terminate-file cannot preserve noise through port reduction",
        )
      }
      let entries : Array[Array[Double]] = required(o, "terminations")
      let loads = entries.map(v => {
        if v.length() != 3 {
          raise Failure("termination must be [port,re,im]")
        }
        (integer(v[0].to_json(), "port"), @lib.complex(v[1], im=v[2]))
      })
      // The surviving network is single-ended; retaining the original modal
      // order or two-port noise records would describe a different model.
      let reduced = doc
        .network_only()
        .terminate_ports(loads, impedance=optional(o, "impedance", false))
      {
        "text": @lib.document(reduced, information=doc.information_lines())
        .write()
        .to_json(),
      }
    }
    "stability" =>
      {
        "stability": doc.network_only().stability().to_json(),
        "source_circles": doc.network_only().stability_circles().to_json(),
        "load_circles": doc
        .network_only()
        .stability_circles(source=false)
        .to_json(),
        "available_gain_circles": doc
        .network_only()
        .gain_circles(optional(o, "gain", 1.0))
        .to_json(),
        "operating_gain_circles": doc
        .network_only()
        .gain_circles(optional(o, "gain", 1.0), source=false)
        .to_json(),
      }
    "gain-check" | "gain-csv" => {
      let mode : String = optional(o, "terminal_mode", "gamma")
      if mode != "gamma" && mode != "impedance" {
        raise Failure("terminal_mode must be gamma or impedance")
      }
      for key in o.keys() {
        let base = key == "command" ||
          key == "ports" ||
          key == "terminal_mode" ||
          key == "start_hz" ||
          key == "end_hz" ||
          key == "minimum_db" ||
          key == "maximum_db"
        let terminal = if mode == "gamma" {
          key == "source" || key == "load"
        } else {
          key == "source_ohms" || key == "load_ohms"
        }
        if !base && !terminal {
          raise Failure("unknown gain check option: " + key)
        }
      }
      let net = doc.network_only()
      let (points, matching) : (Array[@lib.TransducerGainPoint], Json) = if mode ==
        "gamma" {
        let source = match o.get("source") {
          Some(_) => complex_option(o, "source")
          None => @lib.complex(0.0)
        }
        let load = match o.get("load") {
          Some(_) => complex_option(o, "load")
          None => @lib.complex(0.0)
        }
        (
          net.transducer_gain(source~, load~),
          {
            "source": [source.re, source.im].to_json(),
            "load": [load.re, load.im].to_json(),
          },
        )
      } else {
        let source = complex_option(o, "source_ohms")
        let load = complex_option(o, "load_ohms")
        (
          net.transducer_gain_impedance(source, load),
          {
            "source_ohms": [source.re, source.im].to_json(),
            "load_ohms": [load.re, load.im].to_json(),
          },
        )
      }
      let report = @lib.check_transducer_gain(
        points,
        required(o, "start_hz"),
        required(o, "end_hz"),
        minimum_db?=bound(o, "minimum_db"),
        maximum_db?=bound(o, "maximum_db"),
      )
      if command == "gain-csv" {
        {
          "status": report.status.to_json(),
          "terminal_mode": mode.to_json(),
          "reference_ohms": net.reference_ohms().to_json(),
          "matching": matching,
          "report": report.to_json(),
          "text": @lib.transducer_gain_samples_csv(
            points,
            report.start_hz,
            report.end_hz,
            minimum_db?=report.minimum_db,
            maximum_db?=report.maximum_db,
          ).to_json(),
        }
      } else {
        {
          "status": report.status.to_json(),
          "terminal_mode": mode.to_json(),
          "reference_ohms": net.reference_ohms().to_json(),
          "matching": matching,
          "report": report.to_json(),
        }
      }
    }
    "transducer-gain-impedance" => {
      for key in o.keys() {
        if !(key == "command" ||
          key == "ports" ||
          key == "source_ohms" ||
          key == "load_ohms") {
          raise Failure("unknown impedance gain option: " + key)
        }
      }
      doc
      .network_only()
      .transducer_gain_impedance(
        complex_option(o, "source_ohms"),
        complex_option(o, "load_ohms"),
      )
      .to_json()
    }
    "transducer-gain" => {
      for key in o.keys() {
        if !(key == "command" ||
          key == "ports" ||
          key == "source" ||
          key == "load") {
          raise Failure("unknown transducer gain option: " + key)
        }
      }
      let source = match o.get("source") {
        Some(_) => complex_option(o, "source")
        None => @lib.complex(0.0)
      }
      let load = match o.get("load") {
        Some(_) => complex_option(o, "load")
        None => @lib.complex(0.0)
      }
      doc.network_only().transducer_gain(source~, load~).to_json()
    }
    "noise" =>
      {
        "a": doc.noise_correlation().to_json(),
        "s": doc.noise_correlation(representation="S").to_json(),
        "figure_db": doc.noise_figure(complex_option(o, "source")).to_json(),
        "circles": doc.noise_circles(optional(o, "figure_db", 3.0)).to_json(),
      }
    "cascade" =>
      {
        "text": doc
        .cascade(read_document(right, o, "right_ports"))
        .write()
        .to_json(),
      }
    "deembed" =>
      {
        "text": doc
        .deembed(
          read_document(left, o, "left_ports"),
          read_document(right, o, "right_ports"),
        )
        .write()
        .to_json(),
      }
    "interpolate" =>
      { "text": doc.interpolate(required(o, "frequency_hz")).write().to_json() }
    "inspect" | "validate" =>
      {
        "ports": raw.ports().to_json(),
        "parameter": raw.parameter().to_json(),
        "points": raw.frequency_hz().length().to_json(),
        "frequency_hz": raw.frequency_hz().to_json(),
        "reference_ohms": raw.reference_ohms().to_json(),
        "noise": doc.noise_data().to_json(),
        "noise_reference_ohms": doc.noise_reference_ohms().to_json(),
        "mixed_mode_order": doc.mixed_mode_order().to_json(),
        "information": doc.information_lines().to_json(),
      }
    "dump" =>
      {
        "ports": raw.ports().to_json(),
        "parameter": raw.parameter().to_json(),
        "frequency_hz": raw.frequency_hz().to_json(),
        "reference_ohms": raw.reference_ohms().to_json(),
        "values": Array::makei(raw.frequency_hz().length(), i => raw.matrix(i)).to_json(),
        "mixed_mode_order": doc.mixed_mode_order().to_json(),
      }
    "normalize" => { "text": doc.write().to_json() }
    "legacy" => {
      if !doc.noise_data().is_empty() {
        raise Failure(
          "legacy CLI output cannot discard noise; use normalize or the Document writer",
        )
      }
      if !doc.information_lines().is_empty() {
        raise Failure("legacy output cannot preserve information section")
      }
      {
        "text": doc
        .network_only()
        .write_legacy(
          format=optional(o, "format", "RI"),
          unit=optional(o, "unit", "HZ"),
        )
        .to_json(),
      }
    }
    "diagnostics" =>
      doc
      .network_only()
      .diagnostics(tolerance=optional(o, "tolerance", 1.0e-9))
      .to_json()
    "metrics" =>
      doc
      .network_only()
      .metrics(required_int(o, "output"), required_int(o, "input"))
      .to_json()
    "delay" =>
      doc
      .network_only()
      .group_delay(required_int(o, "output"), required_int(o, "input"))
      .to_json()
    "ripple-check" => {
      for key in o.keys() {
        if !(key == "command" ||
          key == "ports" ||
          key == "start_hz" ||
          key == "end_hz" ||
          key == "input" ||
          key == "output" ||
          key == "maximum_ripple_db") {
          raise Failure("unknown ripple option: " + key)
        }
      }
      doc
      .network_only()
      .check_ripple(
        required(o, "start_hz"),
        required(o, "end_hz"),
        input=required_int(o, "input"),
        output=required_int(o, "output"),
        maximum_ripple_db=required(o, "maximum_ripple_db"),
      )
      .to_json()
    }
    "band-check" => band_report(doc.network_only(), o).to_json()
    "band-csv" => {
      let report = band_report(doc.network_only(), o)
      {
        "text": report.issues_csv().to_json(),
        "status": report.status.to_json(),
      }
    }
    _ => {
      let net = doc.network_only()
      let out = match command {
        "convert" => net.convert(required(o, "parameter"))
        "renormalize" => net.renormalize(required(o, "reference_ohms"))
        "select" => {
          if !doc.noise_data().is_empty() {
            raise Failure(
              "port selection/reordering requires an explicit directional noise transformation",
            )
          }
          let selection : Array[Json] = required(o, "selection")
          net.select_ports(selection.map(j => integer(j, "selection")))
        }
        _ => raise Failure("unknown command")
      }
      {
        "text": @lib.document(
          out,
          noise=doc.noise_data(),
          noise_reference_ohms=doc.noise_reference_ohms(),
          information=doc.information_lines(),
        )
        .write()
        .to_json(),
      }
    }
  }
  result.stringify()
}

///|
pub fn run(
  text : String,
  options : String,
  left : String,
  right : String,
) -> String {
  execute(text, options, left, right) catch {
    e => fail_string(@debug.to_string(e))
  }
}
