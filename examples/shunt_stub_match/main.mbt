///|
// Real library consumer: source -> shunt ABCD -> main-line ABCD -> ZL.
// ABCD is row-major, [V1,I1] = M [V2,-I2]; impedances are physical ohms.
fn consume(
  load : @rf.Complex,
  z0 : Double,
  theta : Double,
  phi : Double,
  kind : @rf.StubTermination,
) -> Json raise {
  let c = @math.cos(theta)
  let s = @math.sin(theta)
  let bs = match kind {
    Open => @math.sin(phi) / @math.cos(phi)
    Short => -@math.cos(phi) / @math.sin(phi)
  }
  let line = @rf.network(
    2,
    [1.0e9],
    [
      [
        @rf.complex(c),
        @rf.complex(0.0, im=z0 * s),
        @rf.complex(0.0, im=s / z0),
        @rf.complex(c),
      ],
    ],
    [z0, z0],
    parameter="ABCD",
  ).convert("S")
  let shunt = @rf.network(
    2,
    [1.0e9],
    [
      [
        @rf.complex(1.0),
        @rf.complex(0.0),
        @rf.complex(0.0, im=bs / z0),
        @rf.complex(1.0),
      ],
    ],
    [z0, z0],
    parameter="ABCD",
  ).convert("S")
  let input = shunt.cascade(line).terminate_ports([(1, load)], impedance=true)
  let gamma = input.matrix(0)[0]
  {
    "distance_radians": theta.to_json(),
    "stub_radians": phi.to_json(),
    "s11": gamma.to_json(),
    "reflection_magnitude": gamma.magnitude().to_json(),
    "metrics": input.metrics(0, 0)[0].to_json(),
  }
}

///|
fn main raise {
  let output : Array[Json] = []
  // 1 GHz is metadata for Network consumption; the synthesis lengths are
  // electrical and have no fabrication length until a propagation model exists.
  for
    (name, load, z0, tolerance) in [
      ("r100", @rf.complex(100.0), 50.0, 1.0e-10),
      ("r25", @rf.complex(25.0), 50.0, 1.0e-10),
      ("quarter_wave", @rf.complex(50.0, im=50.0), 50.0, 1.0e-10),
      ("complex_hand", @rf.complex(100.0, im=50.0), 50.0, 1.0e-10),
      ("capacitive", @rf.complex(25.0, im=-75.0), 50.0, 1.0e-10),
      ("inductive", @rf.complex(75.0, im=25.0), 50.0, 1.0e-10),
      ("high_r", @rf.complex(200.0, im=-30.0), 50.0, 1.0e-10),
      ("skrf_example_load", @rf.complex(60.0, im=-80.0), 50.0, 1.0e-10),
      ("zero_distance", @rf.complex(25.0, im=25.0), 50.0, 1.0e-10),
      ("reference75", @rf.complex(90.0, im=-20.0), 75.0, 1.0e-10),
      ("near_match", @rf.complex(50.0, im=1.0e-6), 50.0, 1.0e-10),
      ("matched", @rf.complex(50.0), 50.0, 1.0e-10),
      ("short_load", @rf.complex(0.0), 50.0, 1.0e-10),
      ("reactive_load", @rf.complex(0.0, im=50.0), 50.0, 1.0e-10),
      ("reactive_negative", @rf.complex(-0.0, im=-75.0), 50.0, 1.0e-10),
      ("subnormal_mismatch", @rf.complex(50.0, im=5.0e-324), 50.0, 1.0e-10),
      ("unresolved_scale", @rf.complex(5.0e-324), 1.0e308, 1.0e-10),
      ("rounded_stub_pole", @rf.complex(1.0e308), 50.0, 1.0e-10),
      ("strict_tolerance", @rf.complex(100.0, im=50.0), 50.0, 1.0e-30),
    ] {
    for kind in [@rf.Open, @rf.Short] {
      let matched = @rf.synthesize_shunt_stub(
        load,
        reference_ohms=z0,
        termination=kind,
        tolerance~,
      )
      let consumed : Array[Json] = []
      for solution in matched.solutions {
        consumed.push(
          consume(
            load,
            z0,
            solution.distance_radians,
            solution.stub_radians,
            kind,
          ),
        )
      }
      if matched.free_distance_stub_radians is Some(phi) {
        for theta in [0.0, 0.3, 0.8, @math.PI / 2.0, 3.0] {
          consumed.push(consume(load, z0, theta, phi, kind))
        }
      }
      output.push({
        "case": name.to_json(),
        "synthesis": matched.to_json(),
        "network_checks": consumed.to_json(),
      })
    }
  }
  println(output.to_json().stringify())
}
