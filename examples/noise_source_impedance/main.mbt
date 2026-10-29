///|
fn main raise {
  // Version2.1 Rn is physical ohm; option R50 is the independent noise
  // reference, whereas [Reference]75/100 describes the deterministic ports.
  let text = "[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Number of Frequencies] 2\n[Two-Port Data Order] 12_21\n[Reference] 75 100\n[Number of Noise Frequencies] 1\n[Network Data]\n1000000 0 0 0 0 0.5 0 0 0\n2000000 0 0 0 0 0.25 0 0 0\n[Noise Data]\n1000000 0 0 0 25\n[End]\n"
  let doc = @rf.parse(text)
  let cases = [
    @rf.complex(50.0),
    @rf.complex(150.0),
    @rf.complex(50.0, im=50.0),
  ].map(source => {
    let report : Json = {
      "source_mode": "impedance",
      "source_ohms": [source.re, source.im].to_json(),
      "noise_reference_ohms": doc.noise_reference_ohms().to_json(),
      "network_reference_ohms": doc.raw_network().reference_ohms().to_json(),
      "frequency_hz": doc.raw_network().frequency_hz().to_json(),
      "figure_db": doc.noise_figure_impedance(source).to_json(),
      "quantity": "source_noise_figure",
      "source_units": "ohm",
      "figure_units": "dB",
    }
    report
  })
  let result : Json = { "input_text": text.to_json(), "cases": cases.to_json() }
  println(result.stringify())
}
