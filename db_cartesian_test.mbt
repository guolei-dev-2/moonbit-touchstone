///|
fn db_close(actual : Double, expected : Double) -> Unit raise {
  assert_true((actual / expected - 1.0).abs() < 5.0e-13)
}

///|
test "DB reader keeps finite Cartesian components beyond radial range" {
  // Independent 90-digit Decimal: 10^(6168/20)/sqrt(2).
  let expected = 1.7761719292909023e308
  for
    (angle, re, im) in [
      (45.0, expected, expected),
      (135.0, -expected, expected),
      (225.0, -expected, -expected),
      (-45.0, expected, -expected),
      (405.0, expected, expected),
    ] {
    let net = @touchstone.parse_legacy(
      "# MHz S DB R 50\n1 6168 \{angle}\n",
      ports=1,
    )
    assert_eq(net.frequency_hz(), [1000000.0])
    assert_eq(net.reference_ohms(), [50.0])
    db_close(net.matrix(0)[0].re, re)
    db_close(net.matrix(0)[0].im, im)
  }
}

///|
test "versioned physical Z DB shares the finite component contract" {
  for version in ["2.0", "2.1"] {
    let text = "[Version] \{version}\n# kHz Z DB R 50\n[Number of Ports] 1\n[Number of Frequencies] 1\n[Reference] 75\n[Network Data]\n1000 6168 45\n[End]\n"
    let doc = @touchstone.parse(text)
    let net = doc.network_only()
    assert_eq(net.parameter(), "Z")
    assert_eq(net.reference_ohms(), [75.0])
    assert_eq(net.frequency_hz(), [1000000.0])
    db_close(net.matrix(0)[0].re, 1.7761719292909023e308)
    db_close(net.matrix(0)[0].im, 1.7761719292909023e308)
    let readback = @touchstone.parse(doc.write()).network_only()
    db_close(readback.matrix(0)[0].re, 1.7761719292909023e308)
  }
}

///|
test "DB writer uses finite logarithmic magnitude with independent fields" {
  for
    (re, im, angle) in [
      (1.6e308, 1.6e308, 45.0),
      (-1.6e308, 1.6e308, 135.0),
      (-1.6e308, -1.6e308, -135.0),
      (1.6e308, -1.6e308, -45.0),
    ] {
    let net = @touchstone.network(
      1,
      [1000000.0],
      [[@touchstone.complex(re, im~)]],
      [50.0],
    )
    let text = net.write_legacy(format="DB", unit="MHZ")
    let lines = text.split("\n").map(x => x.to_owned()).to_array()
    let fields = lines[1].split(" ").map(x => x.to_owned()).to_array()
    assert_eq(fields.length(), 3)
    assert_eq(@string.parse_double(fields[0]), 1.0)
    assert_true(
      (@string.parse_double(fields[1]) - 6167.092699609758).abs() < 2.0e-11,
    )
    assert_true((@string.parse_double(fields[2]) - angle).abs() < 1.0e-12)
    let back = @touchstone.parse_legacy(text, ports=1).matrix(0)[0]
    db_close(back.re, re)
    db_close(back.im, im)
  }
}

///|
test "true component overflow and nonfinite DB input still fail" {
  for
    record in [
      "6168 0", "6168 90", "6168 180", "6200 45", "1e308 45", "Infinity 45", "NaN 45",
    ] {
    try
      @touchstone.parse_legacy("# Hz S DB R 50\n1 \{record}\n", ports=1)
    catch {
      _ => ()
    } noraise {
      _ => fail("expected unrepresentable/nonfinite DB to fail")
    }
  }
}

///|
test "ordinary DB output and MA zero boundaries are preserved" {
  let ordinary = @touchstone.parse_legacy("# MHz S DB R 50\n1 -20 0\n", ports=1)
  assert_eq(ordinary.matrix(0)[0].re, 0.1)
  assert_eq(
    ordinary.write_legacy(format="DB", unit="MHZ"),
    "# MHZ S DB R 50\n1 -20 0\n",
  )
  for (re, im, format) in [(1.6e308, 1.6e308, "MA"), (0.0, 0.0, "DB")] {
    let net = @touchstone.network(1, [1.0], [[@touchstone.complex(re, im~)]], [
      50.0,
    ])
    try net.write_legacy(format~) catch {
      _ => ()
    } noraise {
      _ => fail("expected unrepresentable output field to fail")
    }
  }
  let zero = @touchstone.parse_legacy("# Hz S DB R 50\n1 -1e308 45\n", ports=1)
  assert_eq(zero.matrix(0)[0].re, 0.0)
  assert_eq(zero.matrix(0)[0].im, 0.0)
}
