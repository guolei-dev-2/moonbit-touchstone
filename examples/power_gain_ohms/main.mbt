///|
fn main raise {
  let text = "# GHz S RI R 50\n1 .25 0 2 0 .125 0 -.25 0\n2 .2 0 1.5 0 .1 0 -.2 0\n"
  let net = @rf.parse(text, ports=2).network_only()
  println(
    net
    .transducer_gain_impedance(@rf.complex(50.0), @rf.complex(50.0))
    .to_json()
    .stringify(),
  )
  println(
    net
    .transducer_gain_impedance(
      @rf.complex(100.0, im=20.0),
      @rf.complex(25.0, im=-10.0),
    )
    .to_json()
    .stringify(),
  )
}
