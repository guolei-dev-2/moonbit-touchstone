///|
fn main raise {
  // Synthetic PSD noise model, not measured device or calibration evidence.
  let text = "[Version] 2.1\n# MHz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 4\n[Reference] 75 100\n[Number of Noise Frequencies] 2\n[Begin Information]\nsynthetic noise acceptance run\nsource impedance is referred to noise R50\n[End Information]\n[Network Data]\n1 0.125 0 0.0625 0 0.5 0 0.25 0\n2 0.125 0 0.0625 0 0.5 0 0.25 0\n4 0.125 0 0.0625 0 0.5 0 0.25 0\n5 0.125 0 0.0625 0 0.5 0 0.25 0\n[Noise Data]\n1 0 0 0 25\n5 0 0 0 125\n[End]\n"
  let doc = @rf.parse(text)
  let net = doc.raw_network()
  let result : Json = {
    "input_text": text.to_json(),
    "original": {
      "ports": net.ports().to_json(),
      "parameter": net.parameter().to_json(),
      "points": net.frequency_hz().length().to_json(),
      "frequency_hz": net.frequency_hz().to_json(),
      "reference_ohms": net.reference_ohms().to_json(),
      "noise_reference_ohms": doc.noise_reference_ohms().to_json(),
      "noise": doc.noise_data().to_json(),
      "mixed_mode_order": doc.mixed_mode_order().to_json(),
      "information": doc.information_lines().to_json(),
      "values": Array::makei(net.frequency_hz().length(), i => net.matrix(i)).to_json(),
    },
    "gamma_report": doc
    .check_noise_figure(2.0e6, 4.0e6, @rf.complex(1.0 / 3.0), maximum_db=2.0)
    .to_json(),
    "impedance_report": doc
    .check_noise_figure(
      2.0e6,
      4.0e6,
      @rf.complex(100.0),
      maximum_db=2.0,
      impedance=true,
    )
    .to_json(),
  }
  println(result.stringify())
}
