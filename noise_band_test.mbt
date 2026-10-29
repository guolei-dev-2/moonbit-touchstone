///|
fn noise_band_source() -> @touchstone.Document raise {
  let text = "[Version] 2.1\n# MHz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 4\n[Reference] 75 100\n[Number of Noise Frequencies] 2\n[Begin Information]\nsynthetic noise acceptance run\nsource impedance is referred to noise R50\n[End Information]\n[Network Data]\n1 0.125 0 0.0625 0 0.5 0 0.25 0\n2 0.125 0 0.0625 0 0.5 0 0.25 0\n4 0.125 0 0.0625 0 0.5 0 0.25 0\n5 0.125 0 0.0625 0 0.5 0 0.25 0\n[Noise Data]\n1 0 0 0 25\n5 0 0 0 125\n[End]\n"
  @touchstone.parse(text)
}

///|
test "noise band independent rational NF and complete source conditions" {
  let doc = noise_band_source()
  for impedance in [false, true] {
    let source = if impedance { 100.0 } else { 1.0 / 3.0 }
    let report = doc.check_noise_figure(
      2.0e6,
      4.0e6,
      @touchstone.complex(source),
      maximum_db=2.0,
      impedance~,
    )
    assert_eq(report.status, "fail")
    assert_eq(report.scope, "sampled_points_only")
    assert_eq(report.figure_units, "dB")
    assert_eq(report.network_reference_ohms, [75.0, 100.0])
    assert_eq(report.noise_reference_ohms, 50.0)
    assert_eq(report.noise_records, 2)
    assert_eq(report.source.re, source)
    assert_eq(report.source_mode, if impedance { "impedance" } else { "gamma" })
    assert_eq(
      report.source_units,
      if impedance {
        "ohm"
      } else {
        "dimensionless"
      },
    )
    assert_eq(report.sample_count, 2)
    assert_eq(report.failed_count, 1)
    assert_true(
      report.range_covered && report.start_sampled && report.end_sampled,
    )
    // F=1+Rn/100 from the original noise parameters, not a product round trip.
    for i, db in [1.7609125905568124, 3.010299956639812] {
      let sample = report.samples[i]
      assert_eq(sample.point, i + 1)
      assert_eq(sample.frequency_hz, [2.0e6, 4.0e6][i])
      assert_true((sample.figure_db - db).abs() < 2.0e-12)
      assert_eq(sample.above_maximum, i == 1)
      assert_eq(sample.status, if i == 1 { "fail" } else { "pass" })
    }
    assert_eq(report.highest.unwrap().point, 2)
    assert_eq(doc.noise_data().length(), 2)
  }
}

///|
test "noise band coverage empty singleton and failure precedence" {
  let doc = noise_band_source()
  let source = @touchstone.complex(100.0)
  for
    (start, end, limit, status, count, covered) in [
      (2.0e6, 4.0e6, 4.0, "pass", 2, true),
      (0.0, 2.0e6, 4.0, "inconclusive", 2, false),
      (0.0, 4.0e6, 2.0, "fail", 3, false),
      (2.5e6, 3.5e6, 4.0, "inconclusive", 0, true),
      (2.0e6, 2.0e6, 4.0, "pass", 1, true),
    ] {
    let report = doc.check_noise_figure(
      start,
      end,
      source,
      maximum_db=limit,
      impedance=true,
    )
    assert_eq(report.status, status)
    assert_eq(report.sample_count, count)
    assert_eq(report.range_covered, covered)
    assert_eq(report.highest is None, count == 0)
  }
  let nonaligned = doc.check_noise_figure(
    1.5e6,
    4.5e6,
    source,
    maximum_db=4.0,
    impedance=true,
  )
  assert_true(
    nonaligned.range_covered &&
    !nonaligned.start_sampled &&
    !nonaligned.end_sampled,
  )
  assert_eq(nonaligned.samples.map(x => x.point), [1, 2])
}

///|
test "noise band zero negative upper limits first tie and constant record" {
  let doc = noise_band_source()
  let matched = doc.check_noise_figure(
    1.0e6,
    5.0e6,
    @touchstone.complex(0.0),
    maximum_db=0.0,
  )
  assert_eq(matched.status, "pass")
  assert_eq(matched.failed_count, 0)
  assert_eq(matched.highest.unwrap().point, 0)
  for sample in matched.samples {
    assert_eq(sample.figure_db, 0.0)
  }
  let negative = doc.check_noise_figure(
    1.0e6,
    5.0e6,
    @touchstone.complex(0.0),
    maximum_db=-1.0,
  )
  assert_eq(negative.status, "fail")
  assert_eq(negative.failed_count, 4)
  let constant = @touchstone.document(doc.raw_network(), noise=[
    {
      frequency_hz: 0.0,
      minimum_figure_db: 0.0,
      gamma_opt: @touchstone.complex(0.0),
      resistance_ohms: 50.0,
    },
  ])
  let report = constant.check_noise_figure(
    1.0e6,
    5.0e6,
    @touchstone.complex(100.0),
    maximum_db=2.0,
    impedance=true,
  )
  assert_eq(report.noise_records, 1)
  assert_eq(report.status, "pass")
  assert_eq(report.highest.unwrap().point, 0)
  for sample in report.samples {
    assert_true((sample.figure_db - 1.7609125905568124).abs() < 2.0e-12)
  }
}

///|
test "noise band invalid domain or source never becomes a sampled pass" {
  let doc = noise_band_source()
  for
    (start, end, limit, source, impedance) in [
      (-1.0, 2.0e6, 2.0, 0.0, false),
      (4.0e6, 2.0e6, 2.0, 0.0, false),
      (0.0, 2.0e6, 1.0 / 0.0, 0.0, false),
      (0.0, 2.0e6, 2.0, 1.0, false),
      (0.0, 2.0e6, 2.0, 0.0, true),
    ] {
    try
      doc.check_noise_figure(
        start,
        end,
        @touchstone.complex(source),
        maximum_db=limit,
        impedance~,
      )
    catch {
      _ => ()
    } noraise {
      _ => fail("invalid noise check input accepted")
    }
  }
}

///|
test "noise band missing noise and full-grid interpolation errors remain explicit" {
  let doc = noise_band_source()
  let missing = @touchstone.document(doc.raw_network())
  let uncovered = @touchstone.document(doc.raw_network(), noise=[
    {
      frequency_hz: 2.0e6,
      minimum_figure_db: 0.0,
      gamma_opt: @touchstone.complex(0.0),
      resistance_ohms: 50.0,
    },
    {
      frequency_hz: 4.0e6,
      minimum_figure_db: 0.0,
      gamma_opt: @touchstone.complex(0.0),
      resistance_ohms: 100.0,
    },
  ])
  for candidate in [missing, uncovered] {
    try
      candidate.check_noise_figure(
        2.0e6,
        4.0e6,
        @touchstone.complex(100.0),
        maximum_db=4.0,
        impedance=true,
      )
    catch {
      _ => ()
    } noraise {
      _ => fail("invalid full-grid model was hidden by selected band")
    }
  }
  let zero = @touchstone.document(doc.raw_network(), noise=[
    {
      frequency_hz: 0.0,
      minimum_figure_db: 0.0,
      gamma_opt: @touchstone.complex(0.0),
      resistance_ohms: 0.0,
    },
  ])
  assert_eq(
    zero.check_noise_figure(
      1.0e6,
      5.0e6,
      @touchstone.complex(0.0),
      maximum_db=0.0,
    ).status,
    "pass",
  )
}
