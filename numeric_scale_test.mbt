///|
test "finite complex quotient avoids intermediate range overflow" {
  let z = @touchstone.complex(1.0e308, im=1.0e308).divide(
    @touchstone.complex(1.0, im=1.0),
  )
  assert_true((z.re / 1.0e308 - 1.0).abs() < 1.0e-14)
  assert_eq(z.im, 0.0)
  let q = @touchstone.complex(1.7e308).divide(@touchstone.complex(0.9, im=0.9))
  assert_true((q.re / 9.444444444444444e307 - 1.0).abs() < 1.0e-14)
  assert_true((q.im / -9.444444444444444e307 - 1.0).abs() < 1.0e-14)
}

///|
test "subnormal complex quotient retains representable result" {
  let tiny = 5.0e-324
  let z = @touchstone.complex(tiny, im=tiny).divide(
    @touchstone.complex(1.5, im=1.5),
  )
  assert_eq(z.re, tiny)
  assert_eq(z.im, 0.0)
  let separated = @touchstone.complex(1.0e308, im=1.0e-100).divide(
    @touchstone.complex(1.0),
  )
  assert_eq(separated.re, 1.0e308)
  assert_eq(separated.im, 1.0e-100)
}

///|
test "scaled matrix rejection and network admittance preserve physical contract" {
  for scale in [1.0e-200, 1.0, 1.0e200] {
    let c = (x : Double) => @touchstone.complex(x * scale)
    try
      @touchstone.invert_matrix(2, [c(1.0), c(1.0), c(1.0), c(1.0 + 1.0e-14)])
    catch {
      _ => ()
    } noraise {
      _ => fail("near singular matrix accepted")
    }
  }
  let z = @touchstone.network(
    1,
    [1.0],
    [[@touchstone.complex(1.3e308, im=1.3e308)]],
    [50.0],
    parameter="Z",
  )
  let y = z.convert("Y").matrix(0)[0]
  assert_true((y.re / 3.846153846153847e-309 - 1.0).abs() < 1.0e-14)
  assert_true((y.im / -3.846153846153847e-309 - 1.0).abs() < 1.0e-14)
  for
    denominator in [
      @touchstone.complex(0.0),
      @touchstone.complex(1.0 / 0.0),
      @touchstone.complex(0.0 / 0.0),
    ] {
    try @touchstone.complex(1.0).divide(denominator) catch {
      _ => ()
    } noraise {
      _ => fail("invalid denominator accepted")
    }
  }
}

///|
test "finite component matrix pivot is valid even if its norm overflows" {
  let z = @touchstone.invert_matrix(1, [
      @touchstone.complex(1.3e308, im=1.3e308),
    ])[0]
  assert_true((z.re / 3.846153846153847e-309 - 1.0).abs() < 1.0e-14)
  assert_true((z.im / -3.846153846153847e-309 - 1.0).abs() < 1.0e-14)
}

///|
test "row equilibration avoids overflowing elimination with finite inverse" {
  // A=1e308*[[1,1],[-1,1]], so A^-1=5e-309*[[1,-1],[1,1]].
  let a = 1.0e308
  let c = (x : Double) => @touchstone.complex(x)
  let inv = @touchstone.invert_matrix(2, [c(a), c(a), c(-a), c(a)])
  for i, expected in [5.0e-309, -5.0e-309, 5.0e-309, 5.0e-309] {
    assert_true((inv[i].re / expected - 1.0).abs() < 1.0e-14)
    assert_eq(inv[i].im, 0.0)
  }
}
