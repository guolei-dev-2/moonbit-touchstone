///|
test "legacy admittance normalization preserves finite tiny-over-tiny input" {
  let tiny = 5.0e-324
  let net = @touchstone.parse_legacy(
    "# Hz Y RI R 5e-324\n1 5e-324 0\n",
    ports=1,
  )
  assert_eq(net.parameter(), "Y")
  assert_true((net.matrix(0)[0].re - 1.0).abs() < 1.0e-14)
  assert_eq(net.reference_ohms(), [tiny])
}

///|
test "legacy impedance writer avoids overflowing reciprocal normalization" {
  let tiny = 5.0e-324
  let net = @touchstone.network(
    1,
    [1.0],
    [[@touchstone.complex(tiny)]],
    [tiny],
    parameter="Z",
  )
  let output = net.write_legacy()
  // In a one-port Z legacy record, physical Z=Z0 gives normalized Z=1.
  assert_true(output.contains("1 1 0"))
  let back = @touchstone.parse_legacy(output, ports=1)
  assert_eq(back.matrix(0)[0].re, tiny)
}

///|
test "MA degree periodicity is applied before conversion to radians" {
  // 3.6e21 is exactly representable and an exact integer multiple of 360.
  for angle in ["3.6e21", "-3.6e21"] {
    let net = @touchstone.parse_legacy(
      "# Hz S MA R 50\n1 1 \{angle}\n",
      ports=1,
    )
    let z = net.matrix(0)[0]
    assert_true((z.re - 1.0).abs() < 1.0e-14)
    assert_true(z.im.abs() < 1.0e-14)
  }
}
