///|
fn gain_near(actual : Double?, expected : Double) -> Unit raise {
  guard actual is Some(a) else { fail("missing finite gain") }
  assert_true((a - expected).abs() <= 1.0e-12 * expected.abs().max(1.0))
}

///|
fn gain_fixture(
  matrix : Array[@touchstone.Complex],
) -> @touchstone.Network raise {
  @touchstone.network(2, [1.0e9], [matrix], [50.0, 75.0])
}

///|
test "matched gain and an independent bilateral rational example" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([c(0.25), c(0.125), c(2.0), c(-0.25)])
  gain_near(net.transducer_gain()[0].gain, 4.0)
  let g = net.transducer_gain(source=c(0.5), load=c(0.25))[0]
  // Exact D=115/128 and power numerator=45/16, hence GT=9216/2645.
  assert_eq(g.state, "finite")
  assert_eq(g.frequency_hz, 1.0e9)
  gain_near(g.gain, 9216.0 / 2645.0)
  gain_near(Some(net.matrix(0)[2].re), 2.0)
  assert_eq(net.reference_ohms(), [50.0, 75.0])
}

///|
test "complex mismatches and a quarter-wave ideal thru" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([
    c(0.0),
    @touchstone.complex(0.0, im=-1.0),
    @touchstone.complex(0.0, im=-1.0),
    c(0.0),
  ])
  let g = net.transducer_gain(
      source=@touchstone.complex(0.0, im=0.5),
      load=@touchstone.complex(0.0, im=-0.5),
    )[0]
  gain_near(g.gain, 0.36)
}

///|
test "scaled feedback retains finite gain when numerator and denominator squares overflow" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([c(1.0e200), c(0.0), c(1.0e200), c(0.0)])
  gain_near(net.transducer_gain(source=c(0.5))[0].gain, 3.0)
}

///|
test "positive overflow and underflow keep finite logarithmic gain" {
  let c = (v : Double) => @touchstone.complex(v)
  for
    (amplitude, state, db) in [
      (1.0e200, "overflow", 4000.0),
      (1.0e-200, "underflow", -4000.0),
    ] {
    let point = gain_fixture([c(0.0), c(0.0), c(amplitude), c(0.0)]).transducer_gain()[0]
    assert_eq(point.state, state)
    gain_near(point.gain_db, db)
    assert_eq(point.gain, if state == "overflow" { None } else { Some(0.0) })
  }
}

///|
test "zero and lossless load are distinct from singular feedback" {
  let c = (v : Double) => @touchstone.complex(v)
  let block = gain_fixture([c(0.0), c(0.0), c(0.0), c(0.0)])
  let zero = block.transducer_gain()[0]
  assert_eq(zero.state, "zero")
  assert_eq(zero.gain, Some(0.0))
  assert_eq(zero.gain_db, None)
  let loopnet = gain_fixture([c(2.0), c(0.0), c(1.0), c(0.0)])
  assert_eq(loopnet.transducer_gain(load=c(1.0))[0].state, "zero")
  let singular = loopnet.transducer_gain(source=c(0.5), load=c(1.0))[0]
  assert_eq(singular.state, "singular")
  assert_eq(singular.gain, None)
  assert_eq(singular.gain_db, None)
}

///|
test "invalid passive-power domains and wrong port count raise" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([c(0.0), c(0.0), c(1.0), c(0.0)])
  for
    (source, load) in [
      (c(1.0), c(0.0)),
      (c(-1.0), c(0.0)),
      (c(0.0), c(1.001)),
      (@touchstone.complex(0.9, im=0.9), c(0.0)),
      (c(0.0 / 0.0), c(0.0)),
    ] {
    try net.transducer_gain(source~, load~) catch {
      _ => ()
    } noraise {
      _ => fail("invalid termination accepted")
    }
  }
  let one = @touchstone.network(1, [1.0], [[c(0.0)]], [50.0])
  try one.transducer_gain() catch {
    _ => ()
  } noraise {
    _ => fail("one-port accepted")
  }
}

///|
test "gain consumes other network representations with unequal real references" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([c(0.1), c(0.02), c(0.5), c(-0.1)])
  let expected = net.transducer_gain(source=c(0.2), load=c(-0.3))[0].gain
  for kind in ["Z", "Y", "H", "G", "ABCD", "T"] {
    let result = net.convert(kind).transducer_gain(source=c(0.2), load=c(-0.3))[0]
    gain_near(result.gain, expected.unwrap())
  }
}

///|
test "rank-one large scattering matrix retains lower-order feedback terms" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = gain_fixture([c(1.0e200), c(1.0e200), c(1.0e200), c(1.0e200)])
  // det(S)=0 exactly, so D=1-1e200 and GT tends to (3/4)^2.
  let g = net.transducer_gain(source=c(0.5), load=c(0.5))[0]
  assert_eq(g.state, "finite")
  gain_near(g.gain, 0.5625)
}
