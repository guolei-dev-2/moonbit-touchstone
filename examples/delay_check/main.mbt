///|
fn main raise {
  // Exact quarter-turn samples at a deliberately nonuniform 1/2/4 MHz grid.
  // The existing estimator gives 250 ns, 166.666... ns and 125 ns.
  let net = @rf.network(
    2,
    [1.0e6, 2.0e6, 4.0e6],
    [
      [@rf.complex(0.0), @rf.complex(0.0), @rf.complex(1.0), @rf.complex(0.0)],
      [
        @rf.complex(0.0),
        @rf.complex(0.0),
        @rf.complex(0.0, im=-1.0),
        @rf.complex(0.0),
      ],
      [@rf.complex(0.0), @rf.complex(0.0), @rf.complex(-1.0), @rf.complex(0.0)],
    ],
    [50.0, 50.0],
  )
  let report = net.check_group_delay(
    1.0e6,
    4.0e6,
    input=0,
    output=1,
    minimum_seconds=0.0,
    maximum_seconds=2.0e-7,
  )
  println(report.to_json().stringify())
}
