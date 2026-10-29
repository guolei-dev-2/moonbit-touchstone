///|
/// Actual source noise figure in dB for a finite physical Zs in ohm, Re(Zs)>0.
/// Noise parameters use this Document's noise_reference_ohms, independently
/// of the network port references. The source is constant over original Hz
/// samples; the existing chain-covariance interpolation/domain rules apply.
///
/// With C normalized by 4*kB*T0 and Zs=R+jX, the existing quadratic model is
/// F=[R+C00+2*Re(C01)*R+2*Im(C01)*X+C11*(R²+X²)]/R. This is equivalent to
/// Fmin+Rn/Gs*|Ys-Yopt|² (scikit-rf Network.nf / Haus-Adler covariance).
/// Reuse binary-scaled RF products/summation rather than first rounding Zs to
/// Gamma or overflowing intermediate squares. Nonfinite/nonpositive final
/// linear factors raise; no clipping or whole-Double accuracy is promised.
pub fn Document::noise_figure_impedance(
  self : Document,
  source_ohms : Complex,
) -> Array[Double] raise {
  if self.data.n != 2 || self.noise.is_empty() {
    raise Failure("impedance noise figure requires two-port noise data")
  }
  ignore(checked(source_ohms))
  if source_ohms.re <= 0.0 {
    raise Failure("impedance noise figure requires Re(source)>0 ohm")
  }
  let resistance = gain_scaled(complex(source_ohms.re))
  let reactance = gain_scaled(complex(source_ohms.im))
  self.data.frequencies.map(frequency => {
    let c = interpolated_noise(self, frequency)
    let conductance = gain_scaled(complex(c[3].re))
    // Keep R separately, including when larger noise terms cancel. Diagonal
    // covariance entries are real; the +Im(C01)*X sign follows C01*conj(Zs).
    let numerator = gain_impedance_sum([
      resistance,
      gain_scaled(complex(c[0].re)),
      gain_product(gain_scaled(complex(c[1].re), exponent=1), resistance),
      gain_product(gain_scaled(complex(c[1].im), exponent=1), reactance),
      gain_product(conductance, gain_product(resistance, resistance)),
      gain_product(conductance, gain_product(reactance, reactance)),
    ])
    let coefficient = numerator.z.re / resistance.z.re
    let factor = @math.scalbn(
      coefficient,
      numerator.exponent - resistance.exponent,
    )
    if factor <= 0.0 || !finite(factor) {
      raise Failure("physical-source noise factor is not finite positive")
    }
    10.0 * @math.log10(factor)
  })
}
