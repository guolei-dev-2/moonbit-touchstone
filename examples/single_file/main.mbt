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
  // Synthetic exact-rational reference case; no measured-device claim.
  let text = "[Version] 2.1\n# MHz S RI R 40\n[Number of Ports] 4\n[Number of Frequencies] 2\n[Reference] 50 50 75 75\n[Mixed-Mode Order] C3,4 D1,2 D3,4 C1,2\n[Begin Information]\nsource sweep run A\n\nfixture labels are source annotations\n[End Information]\n[Network Data]\n1 0.0078125 0.0 0.015625 0.00390625 0.0234375 -0.00390625 0.03125 0.0078125 0.0390625 0.01171875 0.0546875 -0.0078125 0.0859375 0.015625 0.1015625 -0.01171875 0.1328125 0.01953125 0.1484375 -0.015625 0.1796875 0.0234375 0.2265625 -0.01953125 0.2421875 0.02734375 0.2890625 -0.0234375 0.3203125 0.03125 0.3359375 -0.02734375\n2 0.00390625 0.0 0.0078125 -0.0078125 0.01171875 0.0078125 0.015625 -0.015625 0.01953125 -0.0234375 0.02734375 0.015625 0.04296875 -0.03125 0.05078125 0.0234375 0.06640625 -0.0390625 0.07421875 0.03125 0.08984375 -0.046875 0.11328125 0.0390625 0.12109375 -0.0546875 0.14453125 0.046875 0.16015625 -0.0625 0.16796875 0.0546875\n[End]\n"
  let original = @rf.parse(text)
  if !original.noise_data().is_empty() {
    fail("this mixed-mode example requires a noise-free source")
  }
  // Public API composition already exists. Preserve document conditions when
  // wrapping the restored network; remove mode descriptors only afterwards.
  let single = @rf.document(
    original.single_ended_network(),
    noise_reference_ohms=original.noise_reference_ohms(),
    information=original.information_lines(),
  )
  let result : Json = {
    "input_text": text.to_json(),
    "original": describe(original),
    "single_ended": describe(single),
    "output_text": single.write().to_json(),
    "metrics": single.network_only().metrics(2, 0).to_json(),
  }
  println(result.stringify())
}
