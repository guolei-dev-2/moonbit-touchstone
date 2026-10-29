///|
fn ohms_noise_document(
  frequencies : Array[Double],
  noise_frequencies : Array[Double],
  resistances : Array[Double],
  optimum : @touchstone.Complex,
  references : Array[Double],
  noise_reference : Double,
) -> @touchstone.Document raise {
  let net = @touchstone.network(
    2,
    frequencies,
    frequencies.map(_ => {
      [
        @touchstone.complex(0.0),
        @touchstone.complex(0.0),
        @touchstone.complex(0.5),
        @touchstone.complex(0.0),
      ]
    }),
    references,
  )
  @touchstone.document(
    net,
    noise=noise_frequencies.mapi((i, frequency) => {
      frequency_hz: frequency,
      minimum_figure_db: 0.0,
      gamma_opt: optimum,
      resistance_ohms: resistances[i],
    }),
    noise_reference_ohms=noise_reference,
  )
}

///|
fn ohms_hand_document() -> @touchstone.Document raise {
  ohms_noise_document(
    [1.0e6, 2.0e6],
    [1.0e6],
    [25.0],
    @touchstone.complex(0.0),
    [75.0, 100.0],
    50.0,
  )
}

///|
fn ohms_assert_curve(
  values : Array[Double],
  factors : Array[Double],
) -> Unit raise {
  assert_eq(values.length(), factors.length())
  for i, factor in factors {
    assert_true((values[i] - 10.0 * @math.log10(factor)).abs() < 1.0e-10)
  }
}

///|
test "physical source NF matches handwritten factors and keeps document references" {
  let doc = ohms_hand_document()
  for
    (source, factor) in [
      (@touchstone.complex(50.0), 1.0),
      (@touchstone.complex(150.0), 5.0 / 3.0),
      (@touchstone.complex(50.0, im=50.0), 3.0 / 2.0),
    ] {
    ohms_assert_curve(doc.noise_figure_impedance(source), [factor, factor])
  }
  assert_eq(doc.raw_network().reference_ohms(), [75.0, 100.0])
  assert_eq(doc.noise_reference_ohms(), 50.0)
  assert_eq(doc.raw_network().frequency_hz(), [1.0e6, 2.0e6])
  let changed = @touchstone.document(
    doc.raw_network().renormalize([50.0, 50.0]),
    noise=doc.noise_data(),
    noise_reference_ohms=doc.noise_reference_ohms(),
  )
  assert_eq(
    changed.noise_figure_impedance(@touchstone.complex(150.0)),
    doc.noise_figure_impedance(@touchstone.complex(150.0)),
  )
}

///|
test "physical source NF follows separate noise reference" {
  let doc = ohms_noise_document(
    [1.0e6],
    [1.0e6],
    [25.0],
    @touchstone.complex(0.0),
    [75.0, 100.0],
    100.0,
  )
  ohms_assert_curve(doc.noise_figure_impedance(@touchstone.complex(50.0)), [
    9.0 / 8.0,
  ])
}

///|
test "physical source NF retains chain covariance interpolation and original order" {
  let doc = ohms_noise_document(
    [1.0e6, 2.0e6, 3.0e6],
    [1.0e6, 3.0e6],
    [25.0, 50.0],
    @touchstone.complex(0.0),
    [75.0, 100.0],
    50.0,
  )
  ohms_assert_curve(doc.noise_figure_impedance(@touchstone.complex(150.0)), [
    5.0 / 3.0,
    2.0,
    7.0 / 3.0,
  ])
  let resampled = doc.interpolate([1.5e6, 2.5e6])
  ohms_assert_curve(
    resampled.noise_figure_impedance(@touchstone.complex(150.0)),
    [11.0 / 6.0, 13.0 / 6.0],
  )
}

///|
test "physical source NF complex optimum fixes cross term sign" {
  let doc = ohms_noise_document(
    [1.0e6],
    [1.0e6],
    [25.0],
    @touchstone.complex(0.0, im=0.5),
    [75.0, 100.0],
    50.0,
  )
  ohms_assert_curve(
    doc.noise_figure_impedance(@touchstone.complex(30.0, im=40.0)),
    [1.0],
  )
  ohms_assert_curve(
    doc.noise_figure_impedance(@touchstone.complex(30.0, im=-40.0)),
    [47.0 / 15.0],
  )
}

///|
test "physical source NF keeps huge and tiny positive resistance without rounded Gamma" {
  let doc = ohms_hand_document()
  for value in doc.noise_figure_impedance(@touchstone.complex(1.0e308)) {
    assert_true((value - 3060.0).abs() < 1.0e-10)
  }
  ohms_assert_curve(doc.noise_figure_impedance(@touchstone.complex(1.0e-300)), [
    2.5e301, 2.5e301,
  ])
  try doc.noise_figure(@touchstone.complex(1.0)) catch {
    _ => ()
  } noraise {
    _ => fail("old Gamma unit-circle domain changed")
  }
}

///|
test "physical source NF rejects invalid inputs and nonrepresentable factor" {
  let doc = ohms_hand_document()
  for
    source in [
      @touchstone.complex(0.0),
      @touchstone.complex(0.0, im=50.0),
      @touchstone.complex(-1.0),
      @touchstone.complex(0.0 / 0.0),
      @touchstone.complex(1.0, im=1.0 / 0.0),
      @touchstone.complex(5.0e-324),
      @touchstone.complex(1.0, im=1.0e308),
    ] {
    try doc.noise_figure_impedance(source) catch {
      _ => ()
    } noraise {
      _ => fail("invalid or unrepresentable physical-source NF accepted")
    }
  }
  let missing = @touchstone.document(doc.raw_network())
  try missing.noise_figure_impedance(@touchstone.complex(50.0)) catch {
    _ => ()
  } noraise {
    _ => fail("missing noise treated as explicit zero noise")
  }
}

///|
test "explicit zero covariance is legal for an extreme positive physical source" {
  let doc = ohms_noise_document(
    [1.0e6],
    [1.0e6],
    [0.0],
    @touchstone.complex(0.0),
    [75.0, 100.0],
    50.0,
  )
  assert_eq(
    doc.noise_figure_impedance(@touchstone.complex(5.0e-324, im=1.0e308)),
    [0.0],
  )
}
