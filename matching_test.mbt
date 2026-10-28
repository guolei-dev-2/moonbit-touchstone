///|
fn matching_fixture() -> @touchstone.Network raise {
  let c = (x : Double) => @touchstone.complex(x)
  @touchstone.network(2, [1.0], [[c(0.0), c(0.0), c(1.0), c(0.0)]], [50.0, 75.0])
}

///|
fn matching_relative(actual : Double?, expected : Double) -> Unit raise {
  guard actual is Some(value) else { fail("missing positive gain") }
  assert_true((value - expected).abs() <= expected * 3.0e-14)
}

///|
test "passive near-circle complex matching preserves exact positive power margin" {
  let net = matching_fixture()
  // x=1-2^-53, y=2^-26-2^-79. Exact binary64-input margin is
  // 3*2^-106-2^-158, independently computed with Fraction.
  let x = 0.9999999999999999
  let y = 1.4901161193847655e-8
  let margin = 3.697785493223493e-32
  for (re, im) in [(x, y), (-x, y), (y, x), (y, -x)] {
    let gamma = @touchstone.complex(re, im~)
    matching_relative(net.transducer_gain(source=gamma)[0].gain, margin)
    matching_relative(net.transducer_gain(load=gamma)[0].gain, margin)
    matching_relative(
      net.transducer_gain(source=gamma, load=gamma)[0].gain,
      margin * margin,
    )
  }
  matching_relative(
    net.transducer_gain(source=@touchstone.complex(0.6, im=0.7999999999999998))[0].gain,
    3.108624468950438e-16,
  )
}

///|
test "outside-circle loads cannot become passive through rounded norm or underflow" {
  let net = matching_fixture()
  for
    gamma in [
      @touchstone.complex(0.9999999999999999, im=1.4901161193847656e-8),
      @touchstone.complex(0.6, im=0.8),
      @touchstone.complex(1.0, im=1.0e-200),
      @touchstone.complex(-1.0e-200, im=-1.0),
    ] {
    try net.transducer_gain(load=gamma) catch {
      _ => ()
    } noraise {
      _ => fail("active load accepted")
    }
  }
}
