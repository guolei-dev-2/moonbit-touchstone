///|
// Private file-recipient contract. Raw S only: no conversions or mode recovery.
// Subtraction and magnitude reuse the existing Complex operations (hypot norm).
struct SCompareWitness {
  point : Int
  frequency_hz : Double
  output : Int
  input : Int
  baseline : @lib.Complex
  candidate : @lib.Complex
  delta : @lib.Complex
  absolute_s_delta : Double
} derive(ToJson)

///|
extend SCompareWitness with ToJson::{to_json}

///|
fn s_compare_finite(value : Double) -> Bool {
  !value.is_nan() && !value.is_inf()
}

///|
fn s_compare_values(
  baseline : @lib.Network,
  candidate : @lib.Network,
  limit : Double,
) -> (Json, Bool) raise {
  let n = baseline.ports()
  let frequencies = baseline.frequency_hz()
  let maxima : Array[SCompareWitness?] = Array::make(n * n, None)
  let exceeded_by_channel = Array::make(n * n, 0)
  let mut maximum : SCompareWitness? = None
  let mut exceeded = 0
  // Both validated Networks have at least one point and N>=1. Count every
  // paired element; the report detail is bounded by N*N, not a sampling cap.
  for point, frequency_hz in frequencies {
    let a = baseline.matrix(point)
    let b = candidate.matrix(point)
    for k in 0..<(n * n) {
      let delta = b[k].sub(a[k])
      let magnitude = delta.magnitude()
      if !s_compare_finite(delta.re) ||
        !s_compare_finite(delta.im) ||
        !s_compare_finite(magnitude) {
        raise Failure(
          "s-compare non-finite delta or magnitude at point \{point}, output \{k / n}, input \{k % n}",
        )
      }
      if magnitude > limit {
        exceeded += 1
        exceeded_by_channel[k] += 1
      }
      let witness : SCompareWitness = {
        point,
        frequency_hz,
        output: k / n,
        input: k % n,
        baseline: a[k],
        candidate: b[k],
        delta,
        absolute_s_delta: magnitude,
      }
      // Strict replacement keeps the earliest original point; global ties
      // follow (point, output, input), independently of per-channel ordering.
      match maxima[k] {
        None => maxima[k] = Some(witness)
        Some(old) =>
          if magnitude > old.absolute_s_delta {
            maxima[k] = Some(witness)
          }
      }
      match maximum {
        None => maximum = Some(witness)
        Some(old) =>
          if magnitude > old.absolute_s_delta {
            maximum = Some(witness)
          }
      }
    }
  }
  let per_sij = Array::makei(n * n, k => {
    "output": (k / n).to_json(),
    "input": (k % n).to_json(),
    "evaluated_elements": frequencies.length().to_json(),
    "exceeded_elements": exceeded_by_channel[k].to_json(),
    "maximum": maxima[k].unwrap().to_json(),
  })
  (
    {
      "evaluated_elements": (frequencies.length() * n * n).to_json(),
      "exceeded_elements": exceeded.to_json(),
      "maximum": maximum.unwrap().to_json(),
      "per_sij": per_sij.to_json(),
    },
    exceeded > 0,
  )
}

///|
fn s_compare_source(doc : @lib.Document, digest : String, bytes : Int) -> Json {
  let net = doc.raw_network()
  let frequencies = net.frequency_hz()
  let noise_count = doc.noise_data().length()
  {
    "sha256": digest.to_json(),
    "bytes": bytes.to_json(),
    "parameter": net.parameter().to_json(),
    "ports": net.ports().to_json(),
    "frequency_count": frequencies.length().to_json(),
    "frequency_start_hz": frequencies[0].to_json(),
    "frequency_end_hz": frequencies[frequencies.length() - 1].to_json(),
    "reference_ohms": net.reference_ohms().to_json(),
    "mixed_mode_order": doc.mixed_mode_order().to_json(),
    "noise_present": (noise_count > 0).to_json(),
    "noise_record_count": noise_count.to_json(),
    "noise_not_compared": true,
  }
}

///|
fn s_compare(
  baseline_text : String,
  candidate_text : String,
  transport : Map[String, Json],
) -> Json raise {
  for key in transport.keys() {
    if !(key == "command" ||
      key == "request" ||
      key == "baseline_sha256" ||
      key == "baseline_bytes" ||
      key == "candidate_sha256" ||
      key == "candidate_bytes") {
      raise Failure("unknown s-compare transport field: " + key)
    }
  }
  let request_value : Json = required(transport, "request")
  let request = match request_value {
    Object(fields) => fields
    _ => raise Failure("s-compare request must be an object")
  }
  for key in request.keys() {
    if !(key == "ports" ||
      key == "candidate_ports" ||
      key == "maximum_absolute_s_delta" ||
      key == "physical_alignment_declared") {
      raise Failure("unknown s-compare option: " + key)
    }
  }
  let limit : Double = required(request, "maximum_absolute_s_delta")
  if !s_compare_finite(limit) || limit < 0.0 {
    raise Failure("maximum_absolute_s_delta must be finite and nonnegative")
  }
  let declared : Bool = optional(request, "physical_alignment_declared", false)
  // Reuse only the fixed digest/byte-field validation, never the gain replay
  // protocol or its exact-input match gate. Identity is supplied by the host.
  let baseline_digest = gain_receipt_digest(
    required(transport, "baseline_sha256"),
  )
  let candidate_digest = gain_receipt_digest(
    required(transport, "candidate_sha256"),
  )
  let baseline_bytes = gain_receipt_size(
    required_int(transport, "baseline_bytes"),
  )
  let candidate_bytes = gain_receipt_size(
    required_int(transport, "candidate_bytes"),
  )
  let baseline_doc = read_document(baseline_text, request, "ports")
  let candidate_doc = read_document(candidate_text, request, "candidate_ports")
  let baseline = baseline_doc.raw_network()
  let candidate = candidate_doc.raw_network()
  let reasons : Array[String] = []
  if baseline.parameter() != "S" || candidate.parameter() != "S" {
    reasons.push("non_S_representation")
  }
  if !baseline_doc.mixed_mode_order().is_empty() ||
    !candidate_doc.mixed_mode_order().is_empty() {
    reasons.push("mixed_mode")
  }
  if baseline.ports() != candidate.ports() {
    reasons.push("port_count")
  }
  let a_f = baseline.frequency_hz()
  let b_f = candidate.frequency_hz()
  if a_f.length() != b_f.length() {
    reasons.push("frequency_count")
  } else {
    let mut mismatch = false
    for i, value in a_f {
      if value != b_f[i] {
        mismatch = true
      }
    }
    if mismatch {
      reasons.push("frequency_grid")
    }
  }
  let a_r = baseline.reference_ohms()
  let b_r = candidate.reference_ohms()
  let mut reference_mismatch = a_r.length() != b_r.length()
  if !reference_mismatch {
    for i, value in a_r {
      if value != b_r[i] {
        reference_mismatch = true
      }
    }
  }
  if reference_mismatch {
    reasons.push("reference_ohms")
  }
  if !declared {
    reasons.push("physical_alignment_not_declared")
  }
  let (comparison, status) : (Json, String) = if reasons.is_empty() {
    let (detail, exceeds) = s_compare_values(baseline, candidate, limit)
    (detail, if exceeds { "exceeds" } else { "within" })
  } else {
    (null, "incompatible")
  }
  {
    "kind": "s_comparison_report",
    "scope": "deterministic_S_only",
    "status": status.to_json(),
    "sources": {
      "baseline": s_compare_source(
        baseline_doc, baseline_digest, baseline_bytes,
      ),
      "candidate": s_compare_source(
        candidate_doc, candidate_digest, candidate_bytes,
      ),
    },
    "conditions": {
      "pairing": "exact_ordered_parsed_Hz_and_reference_ohms",
      "physical_alignment_declared": declared.to_json(),
      "physical_alignment": if declared {
        "caller_declared_unverified"
      } else {
        "not_declared"
      },
      "physical_certification": false,
      "delta_definition": "candidate_minus_baseline",
      "maximum_absolute_s_delta": limit.to_json(),
      "limit_inclusive": true,
    },
    "incompatibilities": reasons.to_json(),
    "comparison": comparison,
  }
}
