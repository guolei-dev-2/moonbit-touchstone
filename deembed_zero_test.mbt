///|
fn deembed_zero_network(
  matrix : Array[Double],
  refs : Array[Double],
) -> @touchstone.Network raise {
  @touchstone.network(
    2,
    [1.0e9],
    [matrix.map(x => @touchstone.complex(x))],
    refs,
  )
}

///|
fn deembed_zero_near(
  actual : @touchstone.Network,
  expected : Array[Double],
) -> Unit raise {
  for i, value in expected {
    assert_true((actual.matrix(0)[i].re - value).abs() < 2.0e-12)
    assert_true(actual.matrix(0)[i].im.abs() < 2.0e-12)
  }
}

///|
test "invertible through fixtures preserve an opaque Network and Document" {
  let through = deembed_zero_network([0.0, 1.0, 1.0, 0.0], [50.0, 50.0])
  let zero_dut = deembed_zero_network([0.0, 0.0, 0.0, 0.0], [50.0, 50.0])
  deembed_zero_near(zero_dut.deembed(through, through), [0.0, 0.0, 0.0, 0.0])
  let document = @touchstone.document(zero_dut, information=["Opaque DUT"])
  let result = document.deembed(
    @touchstone.document(through),
    @touchstone.document(through),
  )
  deembed_zero_near(result.network_only(), [0.0, 0.0, 0.0, 0.0])
  assert_eq(result.noise_data().length(), 0)
  assert_eq(result.information_lines(), ["Opaque DUT"])
  deembed_zero_near(@touchstone.parse(result.write()).network_only(), [
    0.0, 0.0, 0.0, 0.0,
  ])
}

///|
test "zero forward recovery preserves reverse transmission and inner references" {
  let left = deembed_zero_network([0.1, 0.5, 0.4, 0.2], [50.0, 75.0])
  let right = deembed_zero_network([-0.1, 0.6, 0.7, 1.0 / 6.0], [60.0, 100.0])
  // Independent boundary-wave connection of DUT [.25,.3,0,-.2]:
  // dL=19/20, dR=49/50, measured=[29/190,90/931,0,17/210].
  let measured = deembed_zero_network(
    [29.0 / 190.0, 90.0 / 931.0, 0.0, 17.0 / 210.0],
    [50.0, 100.0],
  )
  let result = measured.deembed(left, right)
  deembed_zero_near(result, [0.25, 0.3, 0.0, -0.2])
  assert_eq(result.reference_ohms(), [75.0, 60.0])
  let phase_matrix = measured.matrix(0)
  phase_matrix[1] = @touchstone.complex(0.0, im=90.0 / 931.0)
  let phase = @touchstone.network(2, [1.0e9], [phase_matrix], [50.0, 100.0]).deembed(
    left, right,
  )
  assert_true(phase.matrix(0)[1].re.abs() < 2.0e-12)
  assert_true((phase.matrix(0)[1].im - 0.3).abs() < 2.0e-12)
}

///|
test "zero forward path retains singular fixture and true recovery pole errors" {
  let through = deembed_zero_network([0.0, 1.0, 1.0, 0.0], [50.0, 50.0])
  let zero_dut = deembed_zero_network([0.0, 0.0, 0.0, 0.0], [50.0, 50.0])
  let singular = deembed_zero_network([0.0, 0.0, 0.5, 0.0], [50.0, 50.0])
  try zero_dut.deembed(singular, through) catch {
    _ => ()
  } noraise {
    _ => fail("singular fixture accepted")
  }
  let left = deembed_zero_network([0.0, 0.5, 0.5, 0.5], [50.0, 50.0])
  let pole = deembed_zero_network([-0.5, 0.0, 0.0, 0.0], [50.0, 50.0])
  try pole.deembed(left, through) catch {
    _ => ()
  } noraise {
    _ => fail("true recovery pole accepted")
  }
}
