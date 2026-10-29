///|
fn description(net : @rf.Network) -> Json raise {
  {
    "ports": net.ports().to_json(),
    "parameter": net.parameter().to_json(),
    "frequency_hz": net.frequency_hz().to_json(),
    "reference_ohms": net.reference_ohms().to_json(),
    "values": Array::makei(net.frequency_hz().length(), i => net.matrix(i)).to_json(),
  }
}

///|
fn main raise {
  // Synthetic finite-boundary coefficients, not a device measurement.
  // Versioned Z is physical ohms; its 75-ohm reference does not scale Z.
  let text = "[Version] 2.1\n# MHz Z DB R 50\n[Number of Ports] 1\n[Number of Frequencies] 2\n[Reference] 75\n[Begin Information]\nsynthetic finite Cartesian DB example\n[End Information]\n[Network Data]\n1 6168 45\n2 6168 -135\n[End]\n"
  let doc = @rf.parse(text)
  // A separate public writer receiver has nonzero S entries so all DB fields
  // are representable. Per-port references and 21_12 order survive the file.
  let source = @rf.network(
    2,
    [1000000.0, 2000000.0],
    [
      [
        @rf.complex(1.6e308, im=1.6e308),
        @rf.complex(0.1, im=0.2),
        @rf.complex(-1.6e308, im=1.6e308),
        @rf.complex(-0.3, im=0.4),
      ],
      [
        @rf.complex(1.7e308, im=-1.7e308),
        @rf.complex(-0.2, im=-0.1),
        @rf.complex(-1.6e308, im=-1.6e308),
        @rf.complex(0.4, im=-0.3),
      ],
    ],
    [50.0, 75.0],
  )
  let result : Json = {
    "db_input_text": text.to_json(),
    "decoded": description(doc.network_only()),
    "canonical_ri": doc.write().to_json(),
    "information": doc.information_lines().to_json(),
    "source_network": description(source),
    "legacy_db": source.write_legacy(format="DB", unit="MHZ").to_json(),
  }
  println(result.stringify())
}
