///|
fn gain_band_trace(
  amplitudes : Array[Double],
) -> Array[@touchstone.TransducerGainPoint] raise {
  let c = (x : Double) => @touchstone.complex(x)
  @touchstone.network(
    2,
    Array::makei(amplitudes.length(), i => (i + 1).to_double()),
    amplitudes.map(a => [c(0.0), c(0.0), c(a), c(0.0)]),
    [50.0, 50.0],
  ).transducer_gain()
}

///|
test "gain band locates original worst points and counts zero-power violations" {
  let points = gain_band_trace([0.0, 1.0, 2.0])
  let report = @touchstone.check_transducer_gain(
    points,
    1.0,
    3.0,
    minimum_db=3.0,
    maximum_db=7.0,
  )
  assert_eq(report.status, "fail")
  assert_eq(report.sample_count, 3)
  assert_eq(report.below_minimum_count, 2)
  assert_eq(report.above_maximum_count, 0)
  assert_eq(report.state_counts.get("zero"), Some(1))
  assert_eq(report.lowest.unwrap().point, 0)
  assert_eq(report.lowest.unwrap().state, "zero")
  assert_eq(report.highest.unwrap().point, 2)
  assert_eq(report.highest.unwrap().frequency_hz, 3.0)
  assert_eq(points[0].state, "zero")
}

///|
test "inclusive gain bounds single-point intervals and first ties are preserved" {
  let points = gain_band_trace([1.0, 1.0, 2.0])
  let report = @touchstone.check_transducer_gain(
    points,
    1.0,
    2.0,
    minimum_db=0.0,
    maximum_db=0.0,
  )
  assert_eq(report.status, "pass")
  assert_eq(report.lowest.unwrap().point, 0)
  assert_eq(report.highest.unwrap().point, 0)
  let one = @touchstone.check_transducer_gain(
    points,
    2.0,
    2.0,
    minimum_db=0.0,
    maximum_db=0.0,
  )
  assert_eq(one.status, "pass")
  assert_eq(one.sample_count, 1)
  assert_true(one.start_sampled && one.end_sampled)
}

///|
test "positive gain overflow and underflow remain known through dB" {
  let points = gain_band_trace([1.0e-200, 1.0e200])
  let pass = @touchstone.check_transducer_gain(
    points,
    1.0,
    2.0,
    minimum_db=-5000.0,
    maximum_db=5000.0,
  )
  assert_eq(pass.status, "pass")
  assert_eq(pass.state_counts.get("underflow"), Some(1))
  assert_eq(pass.state_counts.get("overflow"), Some(1))
  let fail = @touchstone.check_transducer_gain(
    points,
    1.0,
    2.0,
    minimum_db=-3000.0,
    maximum_db=3000.0,
  )
  assert_eq(fail.status, "fail")
  assert_eq(fail.below_minimum_count, 1)
  assert_eq(fail.above_maximum_count, 1)
  let zero = gain_band_trace([0.0])
  assert_eq(
    @touchstone.check_transducer_gain(zero, 1.0, 1.0, maximum_db=-5000.0).status,
    "pass",
  )
  assert_eq(
    @touchstone.check_transducer_gain(zero, 1.0, 1.0, minimum_db=-5000.0).status,
    "fail",
  )
}

///|
test "singular points are unknown and known failure takes precedence" {
  let c = (x : Double) => @touchstone.complex(x)
  let points = @touchstone.network(
    2,
    [1.0, 2.0],
    [[c(0.0), c(0.0), c(1.0), c(0.0)], [c(2.0), c(0.0), c(1.0), c(0.0)]],
    [50.0, 50.0],
  ).transducer_gain(source=c(0.5))
  let unknown = @touchstone.check_transducer_gain(
    points,
    1.0,
    2.0,
    minimum_db=-2.0,
  )
  assert_eq(unknown.status, "inconclusive")
  assert_eq(unknown.state_counts.get("singular"), Some(1))
  assert_eq(unknown.lowest.unwrap().point, 0)
  assert_true(unknown.reasons.contains("singular_samples"))
  let failed = @touchstone.check_transducer_gain(
    points,
    1.0,
    2.0,
    minimum_db=0.0,
  )
  assert_eq(failed.status, "fail")
  assert_eq(failed.below_minimum_count, 1)
  assert_true(failed.reasons.contains("singular_samples"))
}

///|
test "coverage empty selection and sampled-only one-point selection are explicit" {
  let points = gain_band_trace([1.0, 1.0, 1.0])
  let partial = @touchstone.check_transducer_gain(
    points,
    0.5,
    3.0,
    minimum_db=-1.0,
  )
  assert_eq(partial.status, "inconclusive")
  assert_true(
    !partial.range_covered && !partial.start_sampled && partial.end_sampled,
  )
  let middle = @touchstone.check_transducer_gain(
    points,
    1.25,
    2.75,
    minimum_db=-1.0,
  )
  assert_eq(middle.status, "pass")
  assert_eq(middle.sample_count, 1)
  assert_true(!middle.start_sampled && !middle.end_sampled)
  let none = @touchstone.check_transducer_gain(
    points,
    1.1,
    1.9,
    minimum_db=-1.0,
  )
  assert_eq(none.status, "inconclusive")
  assert_true(none.range_covered && none.reasons.contains("no_samples"))
  let empty = @touchstone.check_transducer_gain([], 1.0, 2.0, minimum_db=0.0)
  assert_eq(empty.status, "inconclusive")
  assert_true(empty.lowest is None)
}

///|
test "invalid rules frequency order and forged state shapes raise" {
  let points = gain_band_trace([1.0, 2.0])
  for
    (start, end, minimum, maximum) in [
      (-1.0, 2.0, Some(0.0), None),
      (2.0, 1.0, Some(0.0), None),
      (1.0, 2.0, None, None),
      (1.0, 2.0, Some(2.0), Some(1.0)),
      (1.0, 2.0, Some(0.0 / 0.0), None),
    ] {
    try
      @touchstone.check_transducer_gain(
        points,
        start,
        end,
        minimum_db?=minimum,
        maximum_db?=maximum,
      )
    catch {
      _ => ()
    } noraise {
      _ => fail("invalid gain rule accepted")
    }
  }
  let forged : @touchstone.TransducerGainPoint = {
    frequency_hz: 1.0,
    gain: Some(0.0),
    gain_db: Some(0.0),
    state: "finite",
  }
  let unknown : @touchstone.TransducerGainPoint = {
    frequency_hz: 1.0,
    gain: Some(1.0),
    gain_db: Some(0.0),
    state: "future_state",
  }
  let bad_frequency : @touchstone.TransducerGainPoint = {
    frequency_hz: 1.0 / 0.0,
    gain: Some(1.0),
    gain_db: Some(0.0),
    state: "finite",
  }
  for
    trace in [
      [points[0], points[0]],
      [points[1], points[0]],
      [forged],
      [unknown],
      [bad_frequency],
    ] {
    try
      @touchstone.check_transducer_gain(trace, 1.0, 2.0, minimum_db=0.0)
    catch {
      _ => ()
    } noraise {
      _ => fail("invalid trace accepted")
    }
  }
}

///|
test "gain report respects the network-sized 100000 point trace boundary" {
  let points : Array[@touchstone.TransducerGainPoint] = Array::makei(100000, i => {
    frequency_hz: (i + 1).to_double(),
    gain: Some(1.0),
    gain_db: Some(0.0),
    state: "finite",
  })
  let report = @touchstone.check_transducer_gain(
    points,
    1.0,
    100000.0,
    minimum_db=0.0,
  )
  assert_eq(report.status, "pass")
  assert_eq(report.sample_count, 100000)
  points.push({
    frequency_hz: 100001.0,
    gain: Some(1.0),
    gain_db: Some(0.0),
    state: "finite",
  })
  try
    @touchstone.check_transducer_gain(points, 1.0, 100001.0, minimum_db=0.0)
  catch {
    _ => ()
  } noraise {
    _ => fail("trace budget bypassed")
  }
}

///|
test "both Gamma and physical ohm GT traces feed the same report contract" {
  let c = (x : Double) => @touchstone.complex(x)
  let net = @touchstone.network(
    2,
    [1.0, 2.0],
    [[c(0.0), c(0.0), c(1.0), c(0.0)], [c(0.0), c(0.0), c(2.0), c(0.0)]],
    [50.0, 50.0],
  )
  let gamma = @touchstone.check_transducer_gain(
    net.transducer_gain(source=c(0.5)),
    1.0,
    2.0,
    minimum_db=-2.0,
    maximum_db=5.0,
  )
  let ohms = @touchstone.check_transducer_gain(
    net.transducer_gain_impedance(c(150.0), c(50.0)),
    1.0,
    2.0,
    minimum_db=-2.0,
    maximum_db=5.0,
  )
  assert_eq(gamma.status, "pass")
  assert_eq(ohms.status, gamma.status)
  assert_eq(ohms.lowest.unwrap().point, gamma.lowest.unwrap().point)
  assert_eq(ohms.highest.unwrap().point, gamma.highest.unwrap().point)
}
