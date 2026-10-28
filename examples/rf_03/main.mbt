///|
fn main raise {
  let c = (v : Double) => @rf.complex(v)
  let s = @rf.network(
    4,
    [1.0e9],
    [
      [
        c(0.0),
        c(0.0),
        c(0.8),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.8),
        c(0.8),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.0),
        c(0.8),
        c(0.0),
        c(0.0),
      ],
    ],
    [50.0, 50.0, 50.0, 50.0],
  )
  let mixed = s.to_mixed_mode([(0, 1), (2, 3)])
  println(mixed.mixed_mode_metrics(1, 0).to_json().stringify())
  let amp = @rf.network(2, [1.0e9], [[c(0.1), c(0.02), c(2.0), c(0.2)]], [
    50.0, 50.0,
  ])
  println(amp.stability().to_json().stringify())
  let noisy = @rf.document(amp, noise=[
    {
      frequency_hz: 1.0e9,
      minimum_figure_db: 1.5,
      gamma_opt: @rf.complex(0.2, im=0.1),
      resistance_ohms: 10.0,
    },
  ])
  println(noisy.cascade(noisy).noise_data().to_json().stringify())
}
