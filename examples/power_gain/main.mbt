///|
fn main raise {
  // Synthetic bilateral amplifier. File order is S11,S21,S12,S22.
  let text = "# GHz S RI R 50\n1 .25 0 2 0 .125 0 -.25 0\n2 .2 0 1.5 0 .1 0 -.2 0\n"
  let net = @rf.parse(text, ports=2).network_only()
  println(net.transducer_gain().to_json().stringify())
  println(
    net
    .transducer_gain(source=@rf.complex(0.5), load=@rf.complex(0.25))
    .to_json()
    .stringify(),
  )
}
