///|
// A bounded complex mantissa and an exact binary scale. Local to gain analysis:
// products in the feedback determinant can exceed double although GT is finite.
priv struct GainScaled {
  z : Complex
  exponent : Int
}

///|
fn gain_scaled(z : Complex, exponent? : Int = 0) -> GainScaled {
  let size = z.re.abs().max(z.im.abs())
  if size == 0.0 {
    { z: complex(0.0), exponent: 0, }
  } else {
    let e = component_exponent(size)
    {
      z: complex(@math.scalbn(z.re, -e), im=@math.scalbn(z.im, -e)),
      exponent: exponent + e,
    }
  }
}

///|
fn gain_product(a : GainScaled, b : GainScaled) -> GainScaled {
  gain_scaled(a.z.mul(b.z), exponent=a.exponent + b.exponent)
}

///|
fn gain_difference(a : GainScaled, b : GainScaled) -> GainScaled {
  if b.z.re == 0.0 && b.z.im == 0.0 {
    return a
  }
  if a.z.re == 0.0 && a.z.im == 0.0 {
    return { z: b.z.scale(-1.0), exponent: b.exponent, }
  }
  let e = a.exponent.max(b.exponent)
  let shifted = (v : GainScaled) => {
    complex(
      @math.scalbn(v.z.re, v.exponent - e),
      im=@math.scalbn(v.z.im, v.exponent - e),
    )
  }
  gain_scaled(shifted(a).sub(shifted(b)), exponent=e)
}

///|
fn gain_sum(terms : Array[GainScaled]) -> GainScaled {
  // Cancel large terms before adding small ones. In particular, rank-one S
  // has det(S)=0; forming (1-Gs*S11)*(1-Gl*S22) first can erase both 1 terms.
  for i in 0..<terms.length() {
    for j in (i + 1)..<terms.length() {
      if terms[j].exponent > terms[i].exponent {
        let item = terms[i]
        terms[i] = terms[j]
        terms[j] = item
      }
    }
  }
  let mut total = gain_scaled(complex(0.0))
  for term in terms {
    total = gain_difference(total, {
      z: term.z.scale(-1.0),
      exponent: term.exponent,
    })
  }
  total
}

///|
fn gain_two_sum(a : Double, b : Double) -> (Double, Double) {
  let sum = a + b
  let bv = sum - a
  let av = sum - bv
  (sum, a - av + (b - bv))
}

///|
fn gain_square_parts(x : Double) -> (Double, Double) {
  // Dekker binary64 split (27 bits). Only bounded |x|<1 reaches this
  // helper, so the splitter cannot overflow. No fused operation is required.
  let split = 134217729.0 * x
  let hi = split - (split - x)
  let lo = x - hi
  let product = x * x
  let error1 = product - hi * hi
  let error2 = error1 - lo * hi
  let error3 = error2 - hi * lo
  (product, lo * lo - error3)
}

///|
fn gain_margin(gamma : Complex) -> Double {
  let x = gamma.re.abs()
  let y = gamma.im.abs()
  if x > 1.0 || y > 1.0 {
    return -1.0
  }
  // An axis component equal to 1 and ANY nonzero companion is outside.
  // Preserve that sign even if the companion's square would underflow.
  if x == 1.0 || y == 1.0 {
    return if (x == 1.0 && y == 0.0) || (y == 1.0 && x == 0.0) {
      0.0
    } else {
      -1.0
    }
  }
  let (xx, xe) = gain_square_parts(x)
  let (yy, ye) = gain_square_parts(y)
  // 1-re²-im² is the power factor, not 1-rounded(hypot(re,im))².
  // Error-free TwoSum growth retains cancellation terms near the unit disk.
  // Numerical building blocks: Priest/Shewchuk floating-point expansions.
  let mut expansion : Array[Double] = []
  for term in [1.0, -xx, -xe, -yy, -ye] {
    let next = []
    let mut sum = term
    for component in expansion {
      let (value, error) = gain_two_sum(sum, component)
      if error != 0.0 {
        next.push(error)
      }
      sum = value
    }
    if sum != 0.0 {
      next.push(sum)
    }
    expansion = next
  }
  let mut margin = 0.0
  for component in expansion {
    margin += component
  }
  margin
}

///|
/// Sampled transducer POWER gain P_load/P_available_source. `gain` is linear;
/// gain_db is finite for positive overflow/underflow but absent for true zero
/// and singular feedback. A finite result is not an oscillation/stability test.
pub(all) struct TransducerGainPoint {
  frequency_hz : Double
  gain : Double?
  gain_db : Double?
  state : String
} derive(ToJson)

///|
pub extend TransducerGainPoint with ToJson::{to_json}

///|
/// Two-port gain for fixed Gamma_s (port0) and Gamma_l (port1), each referred
/// to its own positive real port Z0. Defaults are matched. Source |Gamma|<1;
/// load |Gamma|<=1. Unit-circle loads deliver zero power unless D=0, which
/// takes priority. States: finite, zero, singular, overflow, underflow.
/// Qucs technical eqs1.49-1.57: D=(1-S11*Gs)(1-S22*Gl)-S12*S21*Gs*Gl,
/// GT=|S21|²(1-|Gs|²)(1-|Gl|²)/|D|². Matrices are S[out,in].
pub fn Network::transducer_gain(
  self : Network,
  source? : Complex = complex(0.0),
  load? : Complex = complex(0.0),
) -> Array[TransducerGainPoint] raise {
  if self.n != 2 {
    raise Failure("transducer gain requires a two-port")
  }
  ignore(checked(source))
  ignore(checked(load))
  let source_margin = gain_margin(source)
  let load_margin = gain_margin(load)
  if source_margin <= 0.0 || load_margin < 0.0 {
    raise Failure("transducer gain requires |source|<1 and |load|<=1")
  }
  let gs = gain_scaled(source)
  let gl = gain_scaled(load)
  let one = gain_scaled(complex(1.0))
  let s = self.convert("S")
  Array::makei(s.values.length(), i => {
    let m = s.values[i].map(v => gain_scaled(v))
    let negative_source = gain_product(gs, m[0])
    let negative_load = gain_product(gl, m[3])
    let delta = gain_difference(
      gain_product(m[0], m[3]),
      gain_product(m[1], m[2]),
    )
    let d = gain_sum([
      one,
      { z: negative_source.z.scale(-1.0), exponent: negative_source.exponent, },
      { z: negative_load.z.scale(-1.0), exponent: negative_load.exponent, },
      gain_product(gain_product(gs, gl), delta),
    ])
    let (gain, gain_db, state) = if d.z.re == 0.0 && d.z.im == 0.0 {
      (None, None, "singular")
    } else if (m[2].z.re == 0.0 && m[2].z.im == 0.0) || load_margin == 0.0 {
      (Some(0.0), None, "zero")
    } else {
      let norm = (z : Complex) => z.re * z.re + z.im * z.im
      let coefficient = norm(m[2].z) / norm(d.z) * source_margin * load_margin
      let e = m[2].exponent - d.exponent
      let power = @math.scalbn(coefficient, 2 * e)
      let db = 10.0 * @math.log10(coefficient) +
        20.0 * e.to_double() * @math.log10(2.0)
      if power.is_inf() {
        (None, Some(db), "overflow")
      } else if power == 0.0 {
        (Some(0.0), Some(db), "underflow")
      } else {
        (Some(power), Some(db), "finite")
      }
    }
    { frequency_hz: s.frequencies[i], gain, gain_db, state, }
  })
}
