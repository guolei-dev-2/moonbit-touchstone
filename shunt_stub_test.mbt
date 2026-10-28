///|
// Independent physical ABCD forward oracle, not the synthesis reflection roots.
fn stub_assert_forward(
  load : @touchstone.Complex,
  z0 : Double,
  theta : Double,
  phi : Double,
  kind : @touchstone.StubTermination,
) -> Unit raise {
  let c = @math.cos(theta)
  let s = @math.sin(theta)
  let bs = match kind {
    Open => @math.sin(phi) / @math.cos(phi)
    Short => -@math.cos(phi) / @math.sin(phi)
  }
  // P*L, with [V1,I1] = ABCD [V2,-I2], load at output port.
  let a = @touchstone.complex(c)
  let b = @touchstone.complex(0.0, im=z0 * s)
  let cc = @touchstone.complex(0.0, im=(bs * c + s) / z0)
  let d = @touchstone.complex(c - bs * s)
  let zin = a.mul(load).add(b).divide(cc.mul(load).add(d))
  let gamma = zin
    .sub(@touchstone.complex(z0))
    .divide(zin.add(@touchstone.complex(z0)))
  assert_true(gamma.magnitude() < 2.0e-11)
  assert_true(
    zin.scale(1.0 / z0).sub(@touchstone.complex(1.0)).magnitude() < 1.0e-10,
  )
}

///|
fn stub_assert_angle(actual : Double, expected : Double) -> Unit raise {
  let difference = (actual - expected).abs()
  assert_true(difference.min((@math.PI - difference).abs()) < 2.0e-12)
}

///|
fn stub_assert_discrete(result : @touchstone.ShuntStubMatch) -> Unit raise {
  assert_eq(result.state, "finite")
  assert_eq(result.solutions.length(), 2)
  assert_true(result.free_distance_stub_radians is None)
  assert_true(
    result.solutions[0].distance_radians < result.solutions[1].distance_radians,
  )
  for solution in result.solutions {
    assert_true(
      solution.distance_radians >= 0.0 && solution.distance_radians < @math.PI,
    )
    assert_true(
      solution.stub_radians >= 0.0 && solution.stub_radians < @math.PI,
    )
    assert_eq(
      solution.distance_lambda_g,
      solution.distance_radians / (2.0 * @math.PI),
    )
    assert_eq(solution.stub_lambda_g, solution.stub_radians / (2.0 * @math.PI))
    assert_true(solution.normalized_admittance_error <= result.tolerance)
    stub_assert_forward(
      result.load_ohms,
      result.reference_ohms,
      solution.distance_radians,
      solution.stub_radians,
      result.termination,
    )
  }
}

///|
test "shunt stub handwritten resistive loads enumerate both end types" {
  let alpha = @math.atan2(2.0.sqrt(), 1.0)
  let beta = @math.PI / 2.0 - alpha
  for
    (r, distances, opens, shorts) in [
      (
        100.0,
        [alpha, @math.PI - alpha],
        [@math.PI - beta, beta],
        [alpha, @math.PI - alpha],
      ),
      (
        25.0,
        [beta, @math.PI - beta],
        [beta, @math.PI - beta],
        [@math.PI - alpha, alpha],
      ),
    ] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      let result = @touchstone.synthesize_shunt_stub(
        @touchstone.complex(r),
        reference_ohms=50.0,
        termination=kind,
      )
      stub_assert_discrete(result)
      let lengths = match kind {
        Open => opens
        Short => shorts
      }
      for i, solution in result.solutions {
        stub_assert_angle(solution.distance_radians, distances[i])
        stub_assert_angle(solution.stub_radians, lengths[i])
      }
    }
  }
}

///|
test "shunt stub complex hand cases retain quarter wave and ordinary roots" {
  for
    (load, distances) in [
      (
        @touchstone.complex(50.0, im=50.0),
        [@math.PI / 2.0, @math.PI - @math.atan2(1.0, 2.0)],
      ),
      (
        @touchstone.complex(100.0, im=50.0),
        [@math.atan2(3.0, 1.0), 3.0 * @math.PI / 4.0],
      ),
    ] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      let result = @touchstone.synthesize_shunt_stub(
        load,
        reference_ohms=50.0,
        termination=kind,
      )
      stub_assert_discrete(result)
      let lengths = match kind {
        Open => [3.0 * @math.PI / 4.0, @math.PI / 4.0]
        Short => [@math.PI / 4.0, 3.0 * @math.PI / 4.0]
      }
      for i, solution in result.solutions {
        stub_assert_angle(solution.distance_radians, distances[i])
        stub_assert_angle(solution.stub_radians, lengths[i])
      }
    }
  }
}

///|
test "shunt stub complex loads and zero distance pass physical ABCD" {
  for
    (load, z0) in [
      (@touchstone.complex(25.0, im=-75.0), 50.0),
      (@touchstone.complex(75.0, im=25.0), 50.0),
      (@touchstone.complex(200.0, im=-30.0), 50.0),
      (@touchstone.complex(60.0, im=-80.0), 50.0),
      (@touchstone.complex(25.0, im=25.0), 50.0),
      (@touchstone.complex(90.0, im=-20.0), 75.0),
    ] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      stub_assert_discrete(
        @touchstone.synthesize_shunt_stub(
          load,
          reference_ohms=z0,
          termination=kind,
        ),
      )
    }
  }
}

///|
test "shunt stub exact matched result describes continuous distance family" {
  for kind in [@touchstone.Open, @touchstone.Short] {
    let result = @touchstone.synthesize_shunt_stub(
      @touchstone.complex(50.0),
      reference_ohms=50.0,
      termination=kind,
    )
    assert_eq(result.state, "already_matched")
    assert_eq(result.solutions.length(), 0)
    let phi = match result.free_distance_stub_radians {
      Some(phi) => phi
      None => fail("matched continuous family missing")
    }
    assert_eq(
      phi,
      match kind {
        Open => 0.0
        Short => @math.PI / 2.0
      },
    )
    for theta in [0.0, 0.3, 0.8, @math.PI / 2.0, 3.0] {
      stub_assert_forward(result.load_ohms, 50.0, theta, phi, kind)
    }
  }
}

///|
test "shunt stub zero real loads cannot match a real reference" {
  for
    load in [
      @touchstone.complex(0.0),
      @touchstone.complex(0.0, im=50.0),
      @touchstone.complex(-0.0, im=-75.0),
    ] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      let result = @touchstone.synthesize_shunt_stub(
        load,
        reference_ohms=50.0,
        termination=kind,
      )
      assert_eq(result.state, "no_solution")
      assert_eq(result.solutions.length(), 0)
      assert_true(result.free_distance_stub_radians is None)
    }
  }
}

///|
test "shunt stub rejects invalid load reference and tolerance" {
  for
    (load, z0, tolerance) in [
      (@touchstone.complex(-1.0), 50.0, 1.0e-10),
      (@touchstone.complex(0.0 / 0.0), 50.0, 1.0e-10),
      (@touchstone.complex(50.0, im=1.0 / 0.0), 50.0, 1.0e-10),
      (@touchstone.complex(1.0 / 0.0), 50.0, 1.0e-10),
      (@touchstone.complex(50.0), 0.0, 1.0e-10),
      (@touchstone.complex(50.0), -50.0, 1.0e-10),
      (@touchstone.complex(50.0), 1.0 / 0.0, 1.0e-10),
      (@touchstone.complex(50.0), 0.0 / 0.0, 1.0e-10),
      (@touchstone.complex(50.0), 50.0, 0.0),
      (@touchstone.complex(50.0), 50.0, -1.0),
      (@touchstone.complex(50.0), 50.0, 1.0),
      (@touchstone.complex(50.0), 50.0, 1.0 / 0.0),
      (@touchstone.complex(50.0), 50.0, 0.0 / 0.0),
    ] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      try
        @touchstone.synthesize_shunt_stub(
          load,
          reference_ohms=z0,
          termination=kind,
          tolerance~,
        )
      catch {
        _ => ()
      } noraise {
        _ => fail("invalid stub input accepted")
      }
    }
  }
}

///|
test "shunt stub near match and extremes expose numerical limits" {
  for kind in [@touchstone.Open, @touchstone.Short] {
    let near = @touchstone.synthesize_shunt_stub(
      @touchstone.complex(50.0, im=1.0e-6),
      reference_ohms=50.0,
      termination=kind,
    )
    stub_assert_discrete(near)
    let adjacent = @touchstone.synthesize_shunt_stub(
      @touchstone.complex(50.00000000000001),
      reference_ohms=50.0,
      termination=kind,
    )
    assert_true(
      adjacent.state == "finite" || adjacent.state == "numerical_limit",
    )
    if adjacent.state == "finite" {
      stub_assert_discrete(adjacent)
    }
    for
      (load, z0, tol) in [
        (@touchstone.complex(50.0, im=5.0e-324), 50.0, 1.0e-10),
        (@touchstone.complex(5.0e-324), 1.0e308, 1.0e-10),
        (@touchstone.complex(1.0e308), 50.0, 1.0e-10),
        (@touchstone.complex(100.0, im=50.0), 50.0, 1.0e-30),
      ] {
      let result = @touchstone.synthesize_shunt_stub(
        load,
        reference_ohms=z0,
        termination=kind,
        tolerance=tol,
      )
      assert_eq(result.state, "numerical_limit")
      assert_eq(result.solutions.length(), 0)
      assert_true(result.free_distance_stub_radians is None)
    }
  }
}

///|
test "shunt stub common ohm scaling preserves electrical solutions" {
  for scale in [1.0e-150, 1.0e150] {
    for kind in [@touchstone.Open, @touchstone.Short] {
      let result = @touchstone.synthesize_shunt_stub(
        @touchstone.complex(100.0 * scale, im=50.0 * scale),
        reference_ohms=50.0 * scale,
        termination=kind,
      )
      stub_assert_discrete(result)
      stub_assert_angle(
        result.solutions[0].distance_radians,
        @math.atan2(3.0, 1.0),
      )
      stub_assert_angle(
        result.solutions[1].distance_radians,
        3.0 * @math.PI / 4.0,
      )
    }
  }
}
