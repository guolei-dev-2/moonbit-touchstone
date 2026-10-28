///|
fn ohm_fixture(
  matrix : Array[@touchstone.Complex],
  refs? : Array[Double] = [50.0, 50.0],
) -> @touchstone.Network raise {
  @touchstone.network(2, [1.0e9], [matrix], refs)
}

///|
fn ohm_near(actual : Double?, expected : Double) -> Unit raise {
  guard actual is Some(value) else { fail("missing impedance gain") }
  assert_true((value - expected).abs() <= 2.0e-12 * expected.abs())
}

///|
test "physical ohm inputs use each port reference and independent rational gain" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.25), c(0.125), c(2.0), c(-0.25)], refs=[50.0, 75.0])
  ohm_near(net.transducer_gain_impedance(c(50.0), c(75.0))[0].gain, 4.0)
  // Zs=3*R1 -> Gs=1/2, Zl=(5/3)*R2 -> Gl=1/4.
  ohm_near(
    net.transducer_gain_impedance(c(150.0), c(125.0))[0].gain,
    9216.0 / 2645.0,
  )
  assert_eq(net.reference_ohms(), [50.0, 75.0])
}

///|
test "ideal wire accepts very large and minimum-subnormal matched real terminals" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.0), c(1.0), c(1.0), c(0.0)])
  for resistance in [1.0e308, 5.0e-324, 50.0] {
    let point = net.transducer_gain_impedance(c(resistance), c(resistance))[0]
    assert_eq(point.state, "finite")
    ohm_near(point.gain, 1.0)
    assert_true(point.gain_db.unwrap().abs() < 1.0e-11)
  }
}

///|
test "conjugate reactances retain a tiny positive real resistance" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.0), c(1.0), c(1.0), c(0.0)])
  let source = @touchstone.complex(5.0e-324, im=1.0e308)
  let load = @touchstone.complex(5.0e-324, im=-1.0e308)
  ohm_near(net.transducer_gain_impedance(source, load)[0].gain, 1.0)
}

///|
test "physical transfer overflow and underflow preserve logarithmic gain" {
  let c = (v : Double) => @touchstone.complex(v)
  for
    (transfer, state, db) in [
      (1.0e200, "overflow", 4000.0),
      (1.0e-200, "underflow", -4000.0),
    ] {
    let net = ohm_fixture([c(0.0), c(0.0), c(transfer), c(0.0)])
    let point = net.transducer_gain_impedance(c(50.0), c(50.0))[0]
    assert_eq(point.state, state)
    ohm_near(point.gain_db, db)
  }
}

///|
test "zero physical resistance load and exact feedback singularity remain distinct" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.0), c(0.0), c(1.0), c(0.0)])
  for load in [c(0.0), @touchstone.complex(0.0, im=50.0)] {
    let point = net.transducer_gain_impedance(c(50.0), load)[0]
    assert_eq(point.state, "zero")
    assert_eq(point.gain, Some(0.0))
    assert_eq(point.gain_db, None)
  }
  let pole = ohm_fixture([c(2.0), c(0.0), c(1.0), c(0.0)]).transducer_gain_impedance(
      c(150.0),
      c(50.0),
    )[0]
  assert_eq(pole.state, "singular")
  assert_eq(pole.gain, None)
}

///|
test "physical terminal domain rejects active sources loads and nonfinite values" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.0), c(0.0), c(1.0), c(0.0)])
  for
    (source, load) in [
      (c(0.0), c(50.0)),
      (c(-1.0), c(50.0)),
      (c(50.0), c(-5.0e-324)),
      (@touchstone.complex(0.0, im=1.0), c(50.0)),
      (c(1.0 / 0.0), c(50.0)),
    ] {
    try net.transducer_gain_impedance(source, load) catch {
      _ => ()
    } noraise {
      _ => fail("invalid impedance accepted")
    }
  }
  let one = @touchstone.network(1, [1.0], [[c(0.0)]], [50.0])
  try one.transducer_gain_impedance(c(50.0), c(50.0)) catch {
    _ => ()
  } noraise {
    _ => fail("one-port accepted")
  }
}

///|
test "physical impedance gain consumes a non-S network representation" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = ohm_fixture([c(0.25), c(0.125), c(2.0), c(-0.25)], refs=[50.0, 75.0]).convert(
    "Z",
  )
  ohm_near(
    net.transducer_gain_impedance(c(150.0), c(125.0))[0].gain,
    9216.0 / 2645.0,
  )
}

///|
test "physical matching retains constants beside large rank-one scattering" {
  let c = (v : Double) => @touchstone.complex(v)
  let matrix = [c(1.0e100), c(1.0e100), c(1.0e100), c(1.0e100)]
  let point = ohm_fixture(matrix).transducer_gain_impedance(c(50.0), c(50.0))[0]
  // Both terminals match their port references exactly: GT is |S21|².
  ohm_near(point.gain, 1.0e200)
}
