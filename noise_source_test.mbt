///|
fn noise_source_fixture() -> @touchstone.Document raise {
  let c = (v : Double) => @touchstone.complex(v)
  @touchstone.document(
    @touchstone.network(2, [1.0e9], [[c(0.0), c(0.0), c(0.5), c(0.0)]], [
      50.0, 50.0,
    ]),
    noise=[
      {
        frequency_hz: 1.0e9,
        minimum_figure_db: 1.0,
        gamma_opt: c(0.0),
        resistance_ohms: 50.0,
      },
    ],
  )
}

///|
test "noise figure retains a tiny positive source power margin" {
  let doc = noise_source_fixture()
  // Independent Fraction/Decimal(160) evaluation of the original noise
  // parameters: F=10^0.1+4*|Gamma|²/(1-|Gamma|²), Gamma_opt=0, Rn/Zref=1.
  // First source has exact margin 3*2^-106-2^-158 > 0.
  for
    (re, im, expected) in [
      (0.9999999999999999, 1.4901161193847655e-8, 320.34118276990307),
      (0.6, 0.7999999999999999, 164.7746851547134),
    ] {
    let actual = doc.noise_figure(@touchstone.complex(re, im~))[0]
    assert_true((actual - expected).abs() < 2.0e-11)
  }
}

///|
test "noise figure rejects exact unit and strictly outside sources" {
  let doc = noise_source_fixture()
  for
    gamma in [
      @touchstone.complex(1.0),
      @touchstone.complex(-1.0),
      // Adjacent to the legal first source above; margin = -2^-106.
      @touchstone.complex(0.9999999999999999, im=1.4901161193847656e-8),
      @touchstone.complex(1.0, im=5.0e-324),
    ] {
    try doc.noise_figure(gamma) catch {
      _ => ()
    } noraise {
      _ => fail("nonpositive source power accepted for noise figure")
    }
  }
}

///|
test "matched source still gives the original minimum noise figure" {
  let doc = noise_source_fixture()
  let result = doc.noise_figure(@touchstone.complex(0.0))
  assert_eq(result.length(), 1)
  assert_true((result[0] - 1.0).abs() < 1.0e-12)
}
