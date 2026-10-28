///|
fn main raise {
  let net = @rf.parse(
    "# GHz S RI R 50\n1 .25 0 2 0 .125 0 -.25 0\n2 .2 0 1.5 0 .1 0 -.2 0\n",
    ports=2,
  ).network_only()
  let points = net.transducer_gain_impedance(
    @rf.complex(100.0, im=20.0),
    @rf.complex(25.0, im=-10.0),
  )
  // A table may contain passing samples although the whole sampled report fails.
  println(
    @rf.transducer_gain_samples_csv(
      points,
      1.0e9,
      2.0e9,
      minimum_db=4.0,
      maximum_db=7.0,
    ),
  )
}
