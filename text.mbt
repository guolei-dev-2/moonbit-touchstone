///|
priv struct TextOptions {
  factor : Double
  kind : String
  format : String
  reference : Array[Double]
}

///|
// Validate before UTF-16 slicing: Touchstone is ASCII, not arbitrary Unicode.
// The cap bounds token allocation, not merely the final network array.
fn text_lines(text : String) -> Array[String] raise {
  if text.length() > 64000000 {
    raise Failure("text exceeds 64 million characters")
  }
  let normalized = StringBuilder()
  let mut previous_cr = false
  let mut lines = 1
  let mut width = 0
  for c in text {
    if c == '\r' || (c == '\n' && !previous_cr) {
      lines += 1
      width = 0
      if lines > 1000000 {
        raise Failure("text exceeds one million lines")
      }
      normalized.write_char('\n')
    } else if c == '\n' {
      // CRLF is one physical line, including inside preserved information.
      ()
    } else if c == '\t' || (c >= ' ' && c <= '~') {
      width += 1
      if width > 262144 {
        raise Failure("text line exceeds 262144 characters")
      }
      normalized.write_char(c)
    } else {
      raise Failure("Touchstone requires printable ASCII, tab and line endings")
    }
    previous_cr = c == '\r'
  }
  normalized.to_string().split("\n").map(x => x.to_owned()).to_array()
}

///|
fn uncomment(line : String) -> String {
  let end = line.find("!").unwrap_or(line.length())
  line[:end].trim().to_owned()
}

///|
fn words(line : String) -> Array[String] {
  let result = []
  let mut start = 0
  for i in 0..<=line.length() {
    if i == line.length() || line[i] == ' ' || line[i] == '\t' {
      if start < i {
        result.push(line[start:i].to_owned())
      }
      start = i + 1
    }
  }
  result
}

///|
fn number(token : String) -> Double raise {
  if token.contains("_") {
    raise Failure("underscores are not Touchstone numbers")
  }
  let x = @string.parse_double(token)
  if !finite(x) {
    raise Failure("non-finite numeric field")
  }
  x
}

///|
fn unit_factor(unit : String) -> Double raise {
  match unit.to_upper() {
    "HZ" => 1.0
    "KHZ" => 1000.0
    "MHZ" => 1000000.0
    "GHZ" => 1000000000.0
    _ => raise Failure("unsupported frequency unit")
  }
}

///|
fn read_options(line : String) -> TextOptions raise {
  let tokens = words(line[1:].to_owned())
  let mut unit = "GHZ"
  let mut kind = "S"
  let mut format = "MA"
  let refs = []
  let seen : Map[String, Bool] = Map([])
  let mut i = 0
  while i < tokens.length() {
    let token = tokens[i].to_upper()
    let key = match token {
      "HZ" | "KHZ" | "MHZ" | "GHZ" => {
        unit = token
        "unit"
      }
      "S" | "Y" | "Z" | "H" | "G" => {
        kind = token
        "kind"
      }
      "RI" | "MA" | "DB" => {
        format = token
        "format"
      }
      "R" => {
        i += 1
        while i < tokens.length() {
          let next = tokens[i].to_upper()
          if next == "HZ" ||
            next == "KHZ" ||
            next == "MHZ" ||
            next == "GHZ" ||
            next == "S" ||
            next == "Y" ||
            next == "Z" ||
            next == "H" ||
            next == "G" ||
            next == "RI" ||
            next == "MA" ||
            next == "DB" ||
            next == "R" {
            break
          }
          let r = number(tokens[i])
          if r <= 0.0 {
            raise Failure("reference must be positive")
          }
          refs.push(r)
          if refs.length() > 32 {
            raise Failure("too many references")
          }
          i += 1
        }
        if refs.is_empty() {
          raise Failure("R requires a reference resistance")
        }
        if refs.length() > 1 && i != tokens.length() {
          raise Failure("per-port R must end option line")
        }
        i -= 1
        "reference"
      }
      _ => raise Failure("unknown option: " + token)
    }
    if seen.contains(key) {
      raise Failure("duplicate option category: " + key)
    }
    seen[key] = true
    i += 1
  }
  if refs.is_empty() {
    refs.push(50.0)
  }
  { factor: unit_factor(unit), kind, format, reference: refs, }
}

///|
fn references(refs : Array[Double], n : Int) -> Array[Double] raise {
  if refs.length() == 1 {
    Array::make(n, refs[0])
  } else if refs.length() == n {
    refs.copy()
  } else {
    raise Failure("reference count must be one or match ports")
  }
}

///|
fn pair(a : Double, b : Double, format : String) -> Complex raise {
  if format == "RI" {
    return checked(complex(a, im=b))
  }
  let magnitude = if format == "DB" { @math.pow(10.0, a / 20.0) } else { a }
  // Touchstone angles are degrees: reduce the period in that unit before
  // converting to radians, where a huge argument has already lost the phase.
  let angle = b % 360.0 / 180.0 * @math.PI
  if format == "DB" && magnitude.is_inf() {
    // IBIS 2.1 p6 defines DB as 20log10(|z|). The radial magnitude may
    // exceed binary64 while both Cartesian components still fit. 6160dB
    // is exactly the decimal exponent of 1e308; subtract before division
    // and restore that scale only after projecting each component.
    let scaled = @math.pow(10.0, (a - 6160.0) / 20.0)
    let re = scaled * @math.cos(angle) * 1.0e308
    let im = scaled * @math.sin(angle) * 1.0e308
    if !finite(re) || !finite(im) {
      raise Failure("invalid magnitude")
    }
    return complex(re, im~)
  }
  if magnitude < 0.0 || !finite(magnitude) {
    raise Failure("invalid magnitude")
  }
  checked(
    complex(magnitude * @math.cos(angle), im=magnitude * @math.sin(angle)),
  )
}

///|
// IBIS 2.1 p8: legacy Y/Z/H/G are normalized. Scale voltages by sqrt(R)
// and currents by 1/sqrt(R); H maps (I1,V2) -> (V1,I2), G reverses that.
fn legacy_value(
  value : Complex,
  kind : String,
  row : Int,
  col : Int,
  refs : Array[Double],
  inverse? : Bool = false,
) -> Complex raise {
  ignore(checked(value))
  if kind == "S" {
    return value
  }
  let dr = refs[row].sqrt()
  let dc = refs[col].sqrt()
  let row_mul = kind == "Z" ||
    (kind == "H" && row == 0) ||
    (kind == "G" && row == 1)
  let col_mul = kind == "Z" ||
    (kind == "H" && col == 0) ||
    (kind == "G" && col == 1)
  let er = component_exponent(dr)
  let ec = component_exponent(dc)
  let mr = @math.scalbn(dr, -er)
  let mc = @math.scalbn(dc, -ec)
  let multiply_row = row_mul != inverse
  let multiply_col = col_mul != inverse
  let exponent = (if multiply_row { er } else { -er }) +
    (if multiply_col { ec } else { -ec })
  let mantissa = (if multiply_row { mr } else { 1.0 / mr }) *
    (if multiply_col { mc } else { 1.0 / mc })
  // Never materialize a factor (or its reciprocal) outside double range.
  // Scale each Cartesian component separately, retaining widely separated ones.
  let apply = (x : Double) => {
    if x == 0.0 {
      x
    } else {
      let e = component_exponent(x.abs())
      @math.scalbn(@math.scalbn(x, -e) * mantissa, e + exponent)
    }
  }
  checked(complex(apply(value.re), im=apply(value.im)))
}

///|
fn write_pair(
  out : StringBuilder,
  value : Complex,
  format : String,
) -> Unit raise {
  ignore(checked(value))
  if format == "RI" {
    out.write_string(" \{value.re} \{value.im}")
  } else {
    let mag = value.magnitude()
    // -Inf is not portable Touchstone numeric syntax. Use RI/MA for exact zero.
    if format == "DB" && mag == 0.0 {
      raise Failure(
        "zero magnitude cannot be encoded as finite DB; use RI or MA",
      )
    }
    let a = if format == "DB" && mag.is_inf() {
      // Keep finite component scale outside the squared norm and its log.
      // Ordinary finite magnitudes retain their existing formatting path.
      let scale = value.re.abs().max(value.im.abs())
      let re = value.re / scale
      let im = value.im / scale
      20.0 * @math.log10(scale) + 10.0 * @math.log10(re * re + im * im)
    } else if format == "DB" {
      20.0 * @math.log10(mag)
    } else {
      mag
    }
    let b = value.phase() * 180.0 / @math.PI
    if !finite(a) || !finite(b) {
      raise Failure("non-finite formatted value")
    }
    out.write_string(" \{a} \{b}")
  }
}

///|
// Keep serialized output inside the same file-size contract as the reader.
fn bounded_output(out : StringBuilder) -> String raise {
  let result = out.to_string()
  if result.length() > 64000000 {
    raise Failure("serialized text exceeds 64 million characters")
  }
  result
}
