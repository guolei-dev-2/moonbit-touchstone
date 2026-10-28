///|
/// Cartesian complex value. Values admitted to a Network must be finite.
pub(all) struct Complex {
  re : Double
  im : Double
} derive(ToJson)

///|
pub extend Complex with ToJson::{to_json}

///|
pub fn complex(re : Double, im? : Double = 0.0) -> Complex {
  { re, im, }
}

///|
pub fn Complex::add(a : Complex, b : Complex) -> Complex {
  { re: a.re + b.re, im: a.im + b.im, }
}

///|
pub fn Complex::sub(a : Complex, b : Complex) -> Complex {
  { re: a.re - b.re, im: a.im - b.im, }
}

///|
pub fn Complex::mul(a : Complex, b : Complex) -> Complex {
  { re: a.re * b.re - a.im * b.im, im: a.re * b.im + a.im * b.re, }
}

///|
pub fn Complex::scale(a : Complex, x : Double) -> Complex {
  { re: a.re * x, im: a.im * x, }
}

///|
pub fn Complex::conjugate(a : Complex) -> Complex {
  { re: a.re, im: -a.im, }
}

///|
pub fn Complex::magnitude(a : Complex) -> Double {
  @math.hypot(a.re, a.im)
}

///|
pub fn Complex::phase(a : Complex) -> Double {
  @math.atan2(a.im, a.re)
}

///|
fn finite(x : Double) -> Bool {
  !x.is_nan() && !x.is_inf()
}

///|
fn checked(z : Complex) -> Complex raise {
  if !finite(z.re) || !finite(z.im) {
    raise Failure("non-finite complex result")
  }
  z
}

///|
// Binary exponent of a positive finite component, including subnormals.
// Power-of-two scaling preserves mantissas; logarithms can round max_double
// up to exponent 1024 and do not expose subnormal exponents reliably.
fn component_exponent(x : Double) -> Int {
  let exponent = (x.reinterpret_as_uint64() >> 52).to_int() & 0x7ff
  if exponent == 0 {
    ((@math.scalbn(x, 54).reinterpret_as_uint64() >> 52).to_int() & 0x7ff) -
    1023 -
    54
  } else {
    exponent - 1023
  }
}

///|
/// Power-of-two normalization keeps both complex operands' products bounded.
/// Restore their exponent difference only after division. Overflow is reported,
/// never silently installed in a network. Zero is not replaced by an epsilon.
pub fn Complex::divide(a : Complex, b : Complex) -> Complex raise {
  if !finite(a.re) || !finite(a.im) || !finite(b.re) || !finite(b.im) {
    raise Failure("division requires finite complex values")
  }
  let bmax = b.re.abs().max(b.im.abs())
  if bmax == 0.0 {
    raise Failure("zero complex denominator")
  }
  // Independent scalar divisions preserve a small component next to a huge
  // one. Common numerator normalization would otherwise erase that component.
  if b.im == 0.0 {
    return checked({ re: a.re / b.re, im: a.im / b.re, })
  }
  if b.re == 0.0 {
    return checked({ re: a.im / b.im, im: -a.re / b.im, })
  }
  let amax = a.re.abs().max(a.im.abs())
  if amax == 0.0 {
    return complex(0.0)
  }
  let ae = component_exponent(amax)
  let be = component_exponent(bmax)
  let ar = @math.scalbn(a.re, -ae)
  let ai = @math.scalbn(a.im, -ae)
  let br = @math.scalbn(b.re, -be)
  let bi = @math.scalbn(b.im, -be)
  let den = br * br + bi * bi
  checked({
    re: @math.scalbn((ar * br + ai * bi) / den, ae - be),
    im: @math.scalbn((ai * br - ar * bi) / den, ae - be),
  })
}
