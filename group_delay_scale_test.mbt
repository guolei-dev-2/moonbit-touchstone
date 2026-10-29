///|
fn scaled_delay_network(
  frequencies : Array[Double],
  imaginary : Array[Double],
) -> @touchstone.Network raise {
  @touchstone.network(
    2,
    frequencies,
    imaginary.map(y => {
      [
        @touchstone.complex(0.0),
        @touchstone.complex(0.0),
        @touchstone.complex(1.0, im=y),
        @touchstone.complex(0.0),
      ]
    }),
    [50.0, 75.0],
  )
}

///|
fn scaled_delay_close(actual : Double, expected : Double) -> Unit raise {
  assert_true(!actual.is_inf() && !actual.is_nan())
  assert_true((actual / expected - 1.0).abs() < 5.0e-13)
}

///|
test "finite SI seconds survive overflowing phase per Hz quotient" {
  // Independent Decimal atan series on exact binary64 inputs and pi.
  let magnitude = 3.2213319106796408e307
  for (imaginary, sign) in [(1.0e-15, -1.0), (-1.0e-15, 1.0)] {
    let net = scaled_delay_network([0.0, 5.0e-324], [0.0, imaginary])
    let delays = net.group_delay(1, 0)
    assert_eq(delays.length(), 2)
    for delay in delays {
      scaled_delay_close(delay, sign * magnitude)
    }
  }
}

///|
test "fallback keeps nonuniform centered secant and exact zero" {
  let tiny = 5.0e-324
  let net = scaled_delay_network([0.0, tiny, 3.0 * tiny], [0.0, 1.0e-15, 0.0])
  let values = net.group_delay(1, 0)
  scaled_delay_close(values[0], -3.2213319106796408e307)
  assert_eq(values[1], 0.0)
  scaled_delay_close(values[2], 1.6106659553398204e307)
  let middle = net.check_group_delay(
    tiny,
    tiny,
    input=0,
    output=1,
    minimum_seconds=0.0,
    maximum_seconds=0.0,
  )
  assert_eq(middle.status, "pass")
  assert_eq(middle.sample_count, 1)
  assert_eq(middle.samples[0].point, 1)
  assert_eq(middle.samples[0].delay_seconds, 0.0)
  assert_eq(middle.samples[0].aperture_start_hz, 0.0)
  assert_eq(middle.samples[0].aperture_end_hz, 3.0 * tiny)
}

///|
test "complete delay reports retain signed finite bounds and counts" {
  let net = scaled_delay_network([0.0, 5.0e-324], [0.0, 1.0e-15])
  let passed = net.check_group_delay(
    0.0,
    5.0e-324,
    input=0,
    output=1,
    minimum_seconds=-5.0e307,
    maximum_seconds=0.0,
  )
  assert_eq(passed.status, "pass")
  assert_eq(passed.sample_count, 2)
  assert_eq(passed.failed_count, 0)
  assert_true(
    passed.range_covered && passed.start_sampled && passed.end_sampled,
  )
  for sample in passed.samples {
    scaled_delay_close(sample.delay_seconds, -3.2213319106796408e307)
    assert_eq(sample.status, "pass")
  }
  let failed = net.check_group_delay(
    0.0,
    5.0e-324,
    input=0,
    output=1,
    minimum_seconds=0.0,
  )
  assert_eq(failed.status, "fail")
  assert_eq(failed.below_minimum_count, 2)
  assert_eq(failed.failed_count, 2)
  assert_eq(failed.above_maximum_count, 0)
}

///|
test "true final delay overflow and old undefined inputs remain errors" {
  let overflow = scaled_delay_network([0.0, 5.0e-324], [0.0, 1.0e-14])
  try overflow.group_delay(1, 0) catch {
    _ => ()
  } noraise {
    _ => fail("unrepresentable final seconds accepted")
  }
  let one = scaled_delay_network([0.0], [0.0])
  try one.group_delay(1, 0) catch {
    _ => ()
  } noraise {
    _ => fail("one-point group delay accepted")
  }
  let zero = @touchstone.network(
    1,
    [0.0, 5.0e-324],
    [[@touchstone.complex(1.0)], [@touchstone.complex(0.0)]],
    [50.0],
  )
  try zero.group_delay(0, 0) catch {
    _ => ()
  } noraise {
    _ => fail("zero transmission group delay accepted")
  }
}
