///|
fn consume(
  name : String,
  text : String,
  minimum : Double,
  maximum : Double,
) -> Json raise {
  let net = @rf.parse(text).network_only()
  let frequencies = net.frequency_hz()
  let report = net.check_group_delay(
    frequencies[0],
    frequencies[frequencies.length() - 1],
    input=0,
    output=1,
    minimum_seconds=minimum,
    maximum_seconds=maximum,
  )
  {
    "name": name.to_json(),
    "input_text": text.to_json(),
    "network": {
      "ports": net.ports().to_json(),
      "parameter": net.parameter().to_json(),
      "frequency_hz": frequencies.to_json(),
      "reference_ohms": net.reference_ohms().to_json(),
      "values": Array::makei(frequencies.length(), i => net.matrix(i)).to_json(),
    },
    "delay_seconds": net.group_delay(1, 0).to_json(),
    "minimum_seconds": minimum.to_json(),
    "maximum_seconds": maximum.to_json(),
    "report": report.to_json(),
  }
}

///|
fn main raise {
  // Synthetic finite-input boundaries, not instrument or device performance.
  let header = "[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Reference] 50 75\n"
  let two = header +
    "[Number of Frequencies] 2\n[Network Data]\n0 0 0 0 0 1 0 0 0\n"
  let negative = two + "5e-324 0 0 0 0 1 1e-15 0 0\n[End]\n"
  let positive = two + "5e-324 0 0 0 0 1 -1e-15 0 0\n[End]\n"
  let nonuniform = header +
    "[Number of Frequencies] 3\n[Network Data]\n0 0 0 0 0 1 0 0 0\n5e-324 0 0 0 0 1 1e-15 0 0\n1.5e-323 0 0 0 0 1 0 0 0\n[End]\n"
  let result : Json = {
    "cases": [
      consume("negative-two-point", negative, -5.0e307, 0.0),
      consume("positive-two-point", positive, 0.0, 5.0e307),
      consume("nonuniform-return", nonuniform, -5.0e307, 2.0e307),
    ].to_json(),
  }
  println(result.stringify())
}
