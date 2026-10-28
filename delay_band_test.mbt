///|
fn delay_test_network(
  frequencies : Array[Double],
  transmission : Array[@touchstone.Complex],
) -> @touchstone.Network raise {
  @touchstone.network(
    2,
    frequencies,
    transmission.map(z => {
      [
        @touchstone.complex(0.0),
        @touchstone.complex(0.0),
        z,
        @touchstone.complex(0.0),
      ]
    }),
    [50.0, 50.0],
  )
}

///|
test "delay check uniform quarter turns expose existing stencils" {
  let n = delay_test_network([1.0e6, 2.0e6, 3.0e6, 4.0e6], [
    @touchstone.complex(1.0),
    @touchstone.complex(0.0, im=-1.0),
    @touchstone.complex(-1.0),
    @touchstone.complex(0.0, im=1.0),
  ])
  let report = n.check_group_delay(
    1.0e6,
    4.0e6,
    input=0,
    output=1,
    minimum_seconds=0.0,
    maximum_seconds=3.0e-7,
  )
  assert_eq(report.status, "pass")
  assert_eq(report.sample_count, 4)
  assert_eq(report.failed_count, 0)
  assert_true(
    report.range_covered && report.start_sampled && report.end_sampled,
  )
  let old = n.group_delay(1, 0)
  for i, point in report.samples {
    assert_eq(point.point, i)
    assert_true((point.delay_seconds - 2.5e-7).abs() < 1.0e-20)
    assert_eq(point.delay_seconds, old[i])
  }
  assert_eq(report.samples[0].aperture_start_hz, 1.0e6)
  assert_eq(report.samples[0].aperture_end_hz, 2.0e6)
  assert_eq(report.samples[1].aperture_start_hz, 1.0e6)
  assert_eq(report.samples[1].aperture_end_hz, 3.0e6)
  assert_eq(report.samples[3].aperture_start_hz, 3.0e6)
  assert_eq(report.samples[3].aperture_end_hz, 4.0e6)
}

///|
test "delay check nonuniform hand slopes retain original index and outside neighbor" {
  let n = delay_test_network([1.0e6, 2.0e6, 4.0e6], [
    @touchstone.complex(1.0),
    @touchstone.complex(0.0, im=-1.0),
    @touchstone.complex(-1.0),
  ])
  let report = n.check_group_delay(
    1.0e6,
    4.0e6,
    input=0,
    output=1,
    maximum_seconds=2.0e-7,
  )
  assert_eq(report.status, "fail")
  assert_eq(report.above_maximum_count, 1)
  for i, value in [1.0 / 4000000.0, 1.0 / 6000000.0, 1.0 / 8000000.0] {
    assert_true((report.samples[i].delay_seconds - value).abs() < 1.0e-20)
  }
  let one = n.check_group_delay(
    2.0e6,
    2.0e6,
    input=0,
    output=1,
    minimum_seconds=0.0,
  )
  assert_eq(one.status, "pass")
  assert_eq(one.sample_count, 1)
  assert_eq(one.samples[0].point, 1)
  assert_eq(one.samples[0].aperture_start_hz, 1.0e6)
  assert_eq(one.samples[0].aperture_end_hz, 4.0e6)
  assert_true(one.start_sampled && one.end_sampled)
}

///|
test "delay check known violation wins over coverage and empty band cannot pass" {
  let n = delay_test_network([1.0e6, 2.0e6], [
    @touchstone.complex(1.0),
    @touchstone.complex(0.0, im=-1.0),
  ])
  let failed = n.check_group_delay(
    0.0,
    3.0e6,
    input=0,
    output=1,
    maximum_seconds=2.0e-7,
  )
  assert_eq(failed.status, "fail")
  assert_true(!failed.range_covered)
  let uncovered = n.check_group_delay(
    0.0,
    3.0e6,
    input=0,
    output=1,
    maximum_seconds=3.0e-7,
  )
  assert_eq(uncovered.status, "inconclusive")
  assert_eq(uncovered.failed_count, 0)
  let empty = n.check_group_delay(
    1.1e6,
    1.9e6,
    input=0,
    output=1,
    minimum_seconds=0.0,
  )
  assert_eq(empty.status, "inconclusive")
  assert_true(empty.range_covered && !empty.start_sampled && !empty.end_sampled)
  assert_eq(empty.sample_count, 0)
  assert_true(empty.lowest is None && empty.highest is None)
}

///|
test "delay check includes exact zero limits and permits finite negative delay" {
  let zero = delay_test_network([1.0, 2.0, 3.0], [
    @touchstone.complex(1.0),
    @touchstone.complex(1.0),
    @touchstone.complex(1.0),
  ])
  let report = zero.check_group_delay(
    1.0,
    3.0,
    input=0,
    output=1,
    minimum_seconds=0.0,
    maximum_seconds=0.0,
  )
  assert_eq(report.status, "pass")
  for point in report.samples {
    assert_eq(point.delay_seconds, 0.0)
    assert_true(!point.below_minimum && !point.above_maximum)
  }
  assert_eq(report.lowest.unwrap().point, 0)
  assert_eq(report.highest.unwrap().point, 0)
  let negative = delay_test_network([1.0e6, 2.0e6], [
    @touchstone.complex(1.0),
    @touchstone.complex(0.0, im=1.0),
  ])
  let advanced = negative.check_group_delay(
    1.0e6,
    2.0e6,
    input=0,
    output=1,
    minimum_seconds=-3.0e-7,
    maximum_seconds=0.0,
  )
  assert_eq(advanced.status, "pass")
  assert_true(advanced.samples[0].delay_seconds < 0.0)
}

///|
test "delay check validates bands bounds and ports without changing delay domain" {
  let n = delay_test_network([1.0, 2.0], [
    @touchstone.complex(1.0),
    @touchstone.complex(1.0),
  ])
  for
    (start, end, input, output, low, high) in [
      (-1.0, 2.0, 0, 1, Some(0.0), None),
      (2.0, 1.0, 0, 1, Some(0.0), None),
      (0.0 / 0.0, 2.0, 0, 1, Some(0.0), None),
      (1.0, 1.0 / 0.0, 0, 1, Some(0.0), None),
      (1.0, 2.0, -1, 1, Some(0.0), None),
      (1.0, 2.0, 0, 2, Some(0.0), None),
      (1.0, 2.0, 0, 1, None, None),
      (1.0, 2.0, 0, 1, Some(1.0), Some(0.0)),
      (1.0, 2.0, 0, 1, Some(0.0 / 0.0), None),
      (1.0, 2.0, 0, 1, None, Some(1.0 / 0.0)),
    ] {
    try
      n.check_group_delay(
        start,
        end,
        input~,
        output~,
        minimum_seconds?=low,
        maximum_seconds?=high,
      )
    catch {
      _ => ()
    } noraise {
      _ => fail("invalid delay-check query accepted")
    }
  }
}

///|
test "delay check retains full trace zero and sample-count failures" {
  let short = delay_test_network([1.0], [@touchstone.complex(1.0)])
  try
    short.check_group_delay(1.0, 1.0, input=0, output=1, minimum_seconds=0.0)
  catch {
    _ => ()
  } noraise {
    _ => fail("one-point delay accepted")
  }
  let zero_outside = delay_test_network([1.0, 2.0, 3.0], [
    @touchstone.complex(0.0),
    @touchstone.complex(1.0),
    @touchstone.complex(1.0),
  ])
  try
    zero_outside.check_group_delay(
      2.0,
      3.0,
      input=0,
      output=1,
      minimum_seconds=0.0,
    )
  catch {
    _ => ()
  } noraise {
    _ => fail("undefined full trace was silently cropped")
  }
}
