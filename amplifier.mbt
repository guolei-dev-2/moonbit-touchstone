///|
/// Close selected zero-based ports with complex reflection coefficients.
/// impedance=true interprets values as physical ohm instead. Remaining ports
/// retain ascending original order. Uses homogeneous loads D*a=N*b, so even
/// Z=-Z0 (a pole of Gamma=N/D) is allowed when the combined loop is invertible.
/// active terminations are allowed, singular feedback loops are rejected.
pub fn Network::terminate_ports(
  self : Network,
  terminations : Array[(Int, Complex)],
  impedance? : Bool = false,
) -> Network raise {
  if terminations.is_empty() {
    return self.convert("S")
  }
  if terminations.length() >= self.n {
    raise Failure("at least one port must remain")
  }
  let used = Array::make(self.n, false)
  let ts = []
  let numerators = []
  let denominators = []
  for (p, v) in terminations {
    if p < 0 || p >= self.n || used[p] {
      raise Failure("invalid or duplicate terminated port")
    }
    used[p] = true
    ts.push(p)
    let (numerator, denominator) = if impedance {
      ignore(checked(v))
      // Scale the homogeneous numerator/denominator before adding. Do not
      // divide here: D=0 need not make D-N*Stt singular.
      // A binary scale preserves exact cancellation such as Z=-3*Z0,
      // S22=1/2; arbitrary division can manufacture a tiny nonzero pivot.
      let exponent = component_exponent(
        v.re.abs().max(v.im.abs()).max(self.reference[p]),
      )
      let load = complex(
        @math.scalbn(v.re, -exponent),
        im=@math.scalbn(v.im, -exponent),
      )
      let reference = @math.scalbn(self.reference[p], -exponent)
      (load.sub(complex(reference)), load.add(complex(reference)))
    } else {
      (checked(v), complex(1.0))
    }
    numerators.push(numerator)
    denominators.push(denominator)
  }
  let keep = []
  for p in 0..<self.n {
    if !used[p] {
      keep.push(p)
    }
  }
  let s = self.convert("S")
  let t = ts.length()
  let r = keep.length()
  let values = s.values.map(m => {
    let feedback = Array::makei(t * t, k => {
      (if k / t == k % t { denominators[k / t] } else { complex(0.0) }).sub(
        numerators[k / t].mul(m[ts[k / t] * s.n + ts[k % t]]),
      )
    })
    let inverse = invert_matrix(t, feedback)
    Array::makei(r * r, k => {
      let a = keep[k / r]
      let b = keep[k % r]
      let mut v = m[a * s.n + b]
      for i in 0..<t {
        for j in 0..<t {
          v = v.add(
            m[a * s.n + ts[i]]
            .mul(inverse[i * t + j])
            .mul(numerators[j])
            .mul(m[ts[j] * s.n + b]),
          )
        }
      }
      checked(v)
    })
  })
  network(r, s.frequencies, values, keep.map(p => s.reference[p]))
}

///|
pub(all) struct StabilityPoint {
  frequency_hz : Double
  delta_magnitude : Double
  k : Double?
  mu_input : Double?
  mu_output : Double?
  unconditionally_stable : Bool
  msg : Double?
  mag : Double?
  gain_state : String
} derive(ToJson)

///|
pub extend StabilityPoint with ToJson::{to_json}

///|
fn finite_ratio(a : Double, b : Double) -> Double? {
  if b == 0.0 {
    None
  } else {
    let v = a / b
    if finite(v) {
      Some(v)
    } else {
      None
    }
  }
}

///|
/// Rollett K, |det S| and Edwards-Sinsky geometric stability factors.
/// Gains are LINEAR POWER ratios. MAG exists only when K>1 and |det S|<1;
/// unilateral S12=0 uses |S21|²/((1-|S11|²)(1-|S22|²)). None denotes
/// undefined/nonfinite, never a fabricated epsilon; gain_state explains MAG.
pub fn Network::stability(self : Network) -> Array[StabilityPoint] raise {
  if self.n != 2 {
    raise Failure("stability analysis requires a two-port")
  }
  let s = self.convert("S")
  Array::makei(s.values.length(), i => {
    let m = s.values[i]
    let a = m[0].magnitude()
    let b = m[3].magnitude()
    let reflected = m[0].mul(m[3])
    let transmitted = m[1].mul(m[2])
    let d = reflected.sub(transmitted)
    let delta = d.magnitude()
    let cross = transmitted.magnitude()
    let input_margin = (1.0 - a) * (1.0 + a)
    let output_margin = (1.0 - b) * (1.0 + b)
    // Equal to 1-|S11|^2-|S22|^2+|det S|^2, but preserves the small
    // positive matched-port margins near unit reflection and weak feedback.
    let numerator = input_margin * output_margin +
      cross * cross -
      2.0 * reflected.mul(transmitted.conjugate()).re
    let k = finite_ratio(numerator, 2.0 * cross)
    let stable = if cross == 0.0 {
      a < 1.0 && b < 1.0
    } else {
      // K can exceed the largest finite double while this comparison and
      // the physically finite MAG remain well-defined.
      numerator > 2.0 * cross && delta < 1.0
    }
    let mag = if cross == 0.0 && stable {
      finite_ratio(
        m[2].magnitude() * m[2].magnitude(),
        input_margin * output_margin,
      )
    } else if stable {
      // Rationalize MAG and cancel |S12*S21| analytically. Unlike K^2,
      // half and cross stay bounded for a stable two-port. Split the square
      // root product to avoid premature underflow of a small discriminant.
      let half = numerator / 2.0
      let root = (half - cross).max(0.0).sqrt() * (half + cross).sqrt()
      finite_ratio(m[2].magnitude() * m[2].magnitude(), half + root)
    } else {
      None
    }
    {
      frequency_hz: s.frequencies[i],
      delta_magnitude: delta,
      k,
      mu_input: finite_ratio(
        input_margin,
        m[3].sub(d.mul(m[0].conjugate())).magnitude() + cross,
      ),
      mu_output: finite_ratio(
        output_margin,
        m[0].sub(d.mul(m[3].conjugate())).magnitude() + cross,
      ),
      unconditionally_stable: stable,
      msg: finite_ratio(m[2].magnitude(), m[1].magnitude()),
      mag,
      gain_state: if stable {
        if m[1].re == 0.0 && m[1].im == 0.0 {
          "unilateral_mag"
        } else {
          "mag"
        }
      } else {
        "potentially_unstable"
      },
    }
  })
}

///|
/// Circle equation a*|gamma|² - 2Re(conj(b)*gamma)+c=0.
/// This homogeneous form also represents straight lines (a=0), preserving
/// degeneracies instead of dividing by zero. Finite circles include center/radius.
pub(all) struct RfCircle {
  frequency_hz : Double
  a : Double
  b : Complex
  c : Double
  center : Complex?
  radius : Double?
  state : String
} derive(ToJson)

///|
pub extend RfCircle with ToJson::{to_json}

///|
fn rf_circle(f : Double, a : Double, b : Complex, c : Double) -> RfCircle {
  let r2 = b.re * b.re + b.im * b.im - a * c
  let ordinary = a != 0.0 && r2 >= 0.0
  {
    frequency_hz: f,
    a,
    b,
    c,
    center: if ordinary {
      Some(b.scale(1.0 / a))
    } else {
      None
    },
    radius: if ordinary {
      Some(r2.sqrt() / a.abs())
    } else {
      None
    },
    state: if a == 0.0 {
      if b.magnitude() == 0.0 {
        if c == 0.0 {
          "all"
        } else {
          "empty"
        }
      } else {
        "line"
      }
    } else if r2 < 0.0 {
      "empty"
    } else {
      "circle"
    },
  }
}

///|
/// Source/load stability boundary |Gamma_out|=1 / |Gamma_in|=1.
pub fn Network::stability_circles(
  self : Network,
  source? : Bool = true,
) -> Array[RfCircle] raise {
  if self.n != 2 {
    raise Failure("stability circles require two ports")
  }
  let s = self.convert("S")
  Array::makei(s.values.length(), i => {
    let m = s.values[i]
    let x = if source { m[0] } else { m[3] }
    let y = if source { m[3] } else { m[0] }
    let d = m[0].mul(m[3]).sub(m[1].mul(m[2]))
    rf_circle(
      s.frequencies[i],
      x.magnitude() * x.magnitude() - d.magnitude() * d.magnitude(),
      x.sub(d.mul(y.conjugate())).conjugate(),
      1.0 - y.magnitude() * y.magnitude(),
    )
  })
}

///|
/// Available power gain (source=true) or operating power gain (load) contour.
/// gain is a positive LINEAR power ratio. The equation remains valid for
/// bilateral devices and unstable/empty contours; no unilateral approximation.
pub fn Network::gain_circles(
  self : Network,
  gain : Double,
  source? : Bool = true,
) -> Array[RfCircle] raise {
  if self.n != 2 || !finite(gain) || gain <= 0.0 {
    raise Failure("gain circle requires two ports and positive finite gain")
  }
  let s = self.convert("S")
  Array::makei(s.values.length(), i => {
    let m = s.values[i]
    let x = if source { m[0] } else { m[3] }
    let y = if source { m[3] } else { m[0] }
    let d = m[0].mul(m[3]).sub(m[1].mul(m[2]))
    let t = m[2].magnitude() * m[2].magnitude()
    rf_circle(
      s.frequencies[i],
      gain * (x.magnitude() * x.magnitude() - d.magnitude() * d.magnitude()) + t,
      x.sub(d.mul(y.conjugate())).conjugate().scale(gain),
      gain * (1.0 - y.magnitude() * y.magnitude()) - t,
    )
  })
}
