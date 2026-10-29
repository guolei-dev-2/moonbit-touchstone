///|
fn describe(doc : @rf.Document) -> Json raise {
  let net = doc.raw_network()
  {
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
  }
}

///|
fn main raise {
  // Handwritten uncoupled physical Z sweep, not an instrument performance claim.
  let text = "[Version] 2.1\n# MHz Z RI R 37.5\n[Number of Ports] 3\n[Number of Frequencies] 4\n[Reference] 25 50 75\n[Begin Information]\noriginal sweep for frequency-window export\n\nkeep source units and port labels\n[End Information]\n[Network Data]\n0 25.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 100.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 225.0 0.0\n1 50.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 150.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 300.0 0.0\n2 75.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 200.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 375.0 0.0\n4 100.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 250.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 450.0 0.0\n[End]\n"
  let original = @rf.parse(text)
  let cropped = original.crop(1000000.0, 2000000.0)
  let result : Json = {
    "input_text": text.to_json(),
    "query": { "start_hz": 1000000.0, "end_hz": 2000000.0 },
    "original": describe(original),
    "cropped": describe(cropped),
    "cropped_text": cropped.write().to_json(),
    "metrics": cropped.network_only().metrics(0, 0).to_json(),
  }
  println(result.stringify())
}
