///|
test "matched bilateral amplifier retains finite MAG at huge Rollett K" {
  // For S11=S22=0 and c=|S12*S21|<1,
  // K=(1+c*c)/(2*c), so MAG=|S21/S12|*c=|S21|^2.
  for reverse in [1.0e-100, 1.0e-200, 1.0e-300, 5.0e-324] {
    let c = (v : Double) => @touchstone.complex(v)
    let net = @touchstone.network(
      2,
      [1.0],
      [[c(0.0), c(reverse), c(2.0), c(0.0)]],
      [50.0, 50.0],
    )
    let point = net.stability()[0]
    assert_true(point.unconditionally_stable)
    assert_true(point.mag is Some(g) && (g - 4.0).abs() < 1.0e-13)
    assert_eq(point.gain_state, "mag")
  }
}

///|
test "huge finite matched impedance termination is a zero reflection load" {
  let c = (v : Double) => @touchstone.complex(v)
  for reference in [5.0e-324, 1.0e-310, 50.0, 1.0e308] {
    let net = @touchstone.network(
      2,
      [1.0],
      [[c(0.1), c(0.2), c(0.5), c(0.3)]],
      [50.0, reference],
    )
    let closed = net.terminate_ports([(1, c(reference))], impedance=true)
    assert_eq(closed.ports(), 1)
    assert_eq(closed.matrix(0)[0].re, 0.1)
    assert_eq(closed.matrix(0)[0].im, 0.0)
    assert_eq(closed.reference_ohms(), [50.0])
  }
  // ZL=-Z0 makes Gamma infinite, but the full load/network equations
  // remain invertible when S22!=0: Seff=S11-S12*S21/S22.
  let net = @touchstone.network(2, [1.0], [[c(0.1), c(0.2), c(0.5), c(0.5)]], [
    50.0, 50.0,
  ])
  let pole = net.terminate_ports([(1, c(-50.0))], impedance=true)
  assert_true((pole.matrix(0)[0].re + 0.1).abs() < 1.0e-14)
  // For this network ZL=-3Z0 gives Gamma=2 and a genuinely singular loop.
  try net.terminate_ports([(1, c(-150.0))], impedance=true) catch {
    _ => ()
  } noraise {
    _ => fail("singular impedance feedback accepted")
  }
}

///|
test "noise interpolation does not erase a small nonzero noise resistance" {
  let c = (v : Double) => @touchstone.complex(v)
  let net = @touchstone.network(2, [1.0], [[c(0.0), c(0.5), c(0.5), c(0.0)]], [
    50.0, 50.0,
  ])
  for rn in [1.0e-200, 1.0e-14, 0.0] {
    let doc = @touchstone.document(net, noise=[
      {
        frequency_hz: 1.0,
        minimum_figure_db: 0.0,
        gamma_opt: c(0.0),
        resistance_ohms: rn,
      },
    ])
    let point = doc.interpolate([1.0]).noise_data()[0]
    assert_eq(point.resistance_ohms, rn)
  }
}
