///|
fn rf_near(a : Double, b : Double) -> Unit raise {
  assert_true((a - b).abs() < 1.0e-9)
}

///|
test "ABCD ideal thru and unilateral transfer are not routed through singular Z" {
  let c = (v : Double) => @touchstone.complex(v)
  let thru = @touchstone.network(2, [1.0], [[c(0.0), c(1.0), c(1.0), c(0.0)]], [
    50.0, 50.0,
  ])
  let a = thru.convert("ABCD")
  for i, v in [1.0, 0.0, 0.0, 1.0] {
    rf_near(a.matrix(0)[i].re, v)
  }
  let t = thru.convert("T")
  for i, v in [1.0, 0.0, 0.0, 1.0] {
    rf_near(t.matrix(0)[i].re, v)
  }
  for i, z in thru.matrix(0) {
    rf_near(a.convert("S").matrix(0)[i].re, z.re)
  }
  let amp = @touchstone.network(2, [1.0], [[c(0.1), c(0.0), c(2.0), c(0.2)]], [
    50.0, 75.0,
  ])
  let back = amp.convert("ABCD").convert("T").convert("S")
  for i, z in amp.matrix(0) {
    rf_near(back.matrix(0)[i].re, z.re)
  }
  let stability = amp.stability()[0]
  assert_true(stability.unconditionally_stable)
  assert_eq(stability.gain_state, "unilateral_mag")
  assert_eq(stability.msg, None)
  guard stability.mag is Some(g) else { fail("missing unilateral MAG") }
  rf_near(g, 4.0 / (0.99 * 0.96))
  try a.write_legacy() catch {
    _ => ()
  } noraise {
    _ => fail("nonstandard Touchstone ABCD output")
  }
  // T22=0 means S is undefined, but ABCD is still representable. A direct
  // constraint solve must not introduce a false intermediate S singularity.
  let nonscattering = @touchstone.network(
    2,
    [1.0],
    [[c(0.0), c(1.0), c(1.0), c(0.0)]],
    [50.0, 50.0],
    parameter="T",
  )
  let ab = nonscattering.convert("ABCD")
  for i, v in [1.0, 0.0, 0.0, -1.0] {
    rf_near(ab.matrix(0)[i].re, v)
  }
}

///|
test "complex load feedback and singular feedback rejection" {
  let c = (v : Double) => @touchstone.complex(v)
  let s = @touchstone.network(2, [1.0], [[c(0.1), c(0.2), c(0.8), c(0.3)]], [
    50.0, 50.0,
  ])
  let closed = s.terminate_ports([(1, @touchstone.complex(0.2, im=0.1))])
  // Independently computed complex rational 0.1+0.16*(.2+.1i)/(1-.3*(.2+.1i)).
  rf_near(closed.matrix(0)[0].re, 0.13346523459581684)
  rf_near(closed.matrix(0)[0].im, 0.01808931599773884)
  let loopnet = @touchstone.network(
    2,
    [1.0],
    [[c(0.0), c(1.0), c(1.0), c(1.0)]],
    [50.0, 50.0],
  )
  try loopnet.terminate_ports([(1, c(1.0))]) catch {
    _ => ()
  } noraise {
    _ => fail("singular feedback must fail")
  }
}

///|
test "four-port differential thru uses voltage/current normalization" {
  let c = (v : Double) => @touchstone.complex(v)
  // Independent differential conductors 1->3 and 2->4.
  let s = @touchstone.network(
    4,
    [1.0],
    [
      [
        c(0.0),
        c(0.0),
        c(1.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(1.0),
        c(1.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(1.0),
        c(0.0),
        c(0.0),
      ],
    ],
    [50.0, 50.0, 50.0, 50.0],
  )
  let mixed = s.to_mixed_mode([(0, 1), (2, 3)])
  assert_eq(mixed.modal_network().reference_ohms(), [100.0, 100.0, 25.0, 25.0])
  let metric = mixed.mixed_mode_metrics(1, 0)[0]
  rf_near(metric.sdd.re, 1.0)
  rf_near(metric.sdc.magnitude(), 0.0)
  rf_near(metric.scd.magnitude(), 0.0)
  assert_eq(metric.cmrr_definition, "balanced")
  assert_eq(metric.cmrr_state, "finite")
  rf_near(metric.cmrr_db.unwrap(), 0.0)
  assert_eq(
    mixed.mixed_mode_metrics(1, 0, cmrr="input")[0].cmrr_state,
    "positive_infinity",
  )
  assert_eq(
    mixed.mixed_mode_metrics(1, 0, cmrr="output")[0].cmrr_state,
    "positive_infinity",
  )
  let back = @touchstone.parse(mixed.write()).network_only()
  for i, z in s.matrix(0) {
    rf_near(back.matrix(0)[i].re, z.re)
  }
}

///|
test "matched noisy amplifier cascade obeys Friis and noisy fixture deembedding" {
  let c = (v : Double) => @touchstone.complex(v)
  let s1 = @touchstone.network(2, [1.0], [[c(0.0), c(0.0), c(2.0), c(0.0)]], [
    50.0, 50.0,
  ])
  let s2 = @touchstone.network(2, [1.0], [[c(0.0), c(0.05), c(3.0), c(0.0)]], [
    50.0, 50.0,
  ])
  let d1 = @touchstone.document(s1, noise=[
    {
      frequency_hz: 1.0,
      minimum_figure_db: 3.010299956639812,
      gamma_opt: c(0.0),
      resistance_ohms: 25.0,
    },
  ])
  let d2 = @touchstone.document(s2, noise=[
    {
      frequency_hz: 1.0,
      minimum_figure_db: 4.771212547196624,
      gamma_opt: c(0.0),
      resistance_ohms: 50.0,
    },
  ])
  let total = d1.cascade(d2)
  rf_near(total.noise_figure(c(0.0))[0], 3.979400086720376)
  let thru = @touchstone.document(
    @touchstone.network(2, [1.0], [[c(0.0), c(1.0), c(1.0), c(0.0)]], [
      50.0, 50.0,
    ]),
  )
  let recovered = total.deembed(thru, d2)
  rf_near(recovered.noise_data()[0].minimum_figure_db, 3.010299956639812)
  rf_near(recovered.noise_data()[0].resistance_ohms, 25.0)
}

///|
test "noise deembedding rejects indefinite covariance with positive Rn and Fmin" {
  // Independent covariance construction: normalized measured [[2,.2],[.2,.1]]
  // and fixture [[1,0],[0,.09]] are PSD; their difference has determinant -.03.
  let c = (v : Double) => @touchstone.complex(v)
  let thru = @touchstone.network(2, [1.0], [[c(0.0), c(1.0), c(1.0), c(0.0)]], [
    50.0, 50.0,
  ])
  let measured = @touchstone.document(thru, noise=[
    {
      frequency_hz: 1.0,
      minimum_figure_db: 10.0 * @math.log10(1.4 + 2.0 * 0.2.sqrt()),
      gamma_opt: c((1.0 - 0.05.sqrt()) / (1.0 + 0.05.sqrt())),
      resistance_ohms: 100.0,
    },
  ])
  let fixture = @touchstone.document(thru, noise=[
    {
      frequency_hz: 1.0,
      minimum_figure_db: 10.0 * @math.log10(1.6),
      gamma_opt: c(0.7 / 1.3),
      resistance_ohms: 50.0,
    },
  ])
  // The inputs themselves are valid noise models.
  ignore(measured.noise_correlation())
  ignore(fixture.noise_correlation())
  try measured.deembed(fixture, @touchstone.document(thru)) catch {
    _ => ()
  } noraise {
    _ =>
      fail(
        "negative covariance eigenvalue must not be converted to noise parameters",
      )
  }
}
