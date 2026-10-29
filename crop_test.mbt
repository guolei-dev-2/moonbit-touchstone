///|
fn crop_test_document() -> @touchstone.Document raise {
  @touchstone.parse(
    "[Version] 2.1\n# MHz Z RI R 37.5\n[Number of Ports] 3\n[Number of Frequencies] 4\n[Reference] 25 50 75\n[Begin Information]\noriginal sweep for frequency-window export\n\nkeep source units and port labels\n[End Information]\n[Network Data]\n0 25.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 100.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 225.0 0.0\n1 50.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 150.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 300.0 0.0\n2 75.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 200.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 375.0 0.0\n4 100.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 250.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 450.0 0.0\n[End]\n",
  )
}

///|
test "crop exports original complete SI matrices and document conditions" {
  let original = crop_test_document()
  let before = original.write()
  let cropped = original.crop(1000000.0, 2000000.0)
  let net = cropped.raw_network()
  assert_eq(net.ports(), 3)
  assert_eq(net.parameter(), "Z")
  assert_eq(net.frequency_hz(), [1000000.0, 2000000.0])
  assert_eq(net.reference_ohms(), [25.0, 50.0, 75.0])
  assert_eq(cropped.noise_reference_ohms(), 37.5)
  assert_true(cropped.noise_data().is_empty())
  assert_true(cropped.mixed_mode_order().is_empty())
  assert_eq(cropped.information_lines(), [
    "original sweep for frequency-window export", "", "keep source units and port labels",
  ])
  for
    p, expected in [
      [50.0, 0.0, 0.0, 0.0, 150.0, 0.0, 0.0, 0.0, 300.0],
      [75.0, 0.0, 0.0, 0.0, 200.0, 0.0, 0.0, 0.0, 375.0],
    ] {
    for k, z in net.matrix(p) {
      assert_eq(z.re, expected[k])
      assert_eq(z.im, 0.0)
    }
  }
  let readback = @touchstone.parse(cropped.write())
  assert_eq(readback.raw_network().frequency_hz(), net.frequency_hz())
  assert_eq(readback.information_lines(), cropped.information_lines())
  assert_eq(original.write(), before)
}

///|
test "crop uses closed original-point intersection without nearest endpoints" {
  let doc = crop_test_document()
  for
    (start, end, expected) in [
      (0.0, 0.0, [0.0]),
      (4000000.0, 4000000.0, [4000000.0]),
      (1100000.0, 3900000.0, [2000000.0]),
      (0.0, 5000000.0, [0.0, 1000000.0, 2000000.0, 4000000.0]),
    ] {
    assert_eq(doc.crop(start, end).raw_network().frequency_hz(), expected)
  }
  try doc.crop(1100000.0, 1900000.0) catch {
    _ => ()
  } noraise {
    _ => fail("empty crop invented an original point")
  }
  let one = doc.crop(1000000.0, 1000000.0)
  try one.network_only().group_delay(0, 0) catch {
    _ => ()
  } noraise {
    _ => fail("cropping one point made group delay defined")
  }
}

///|
test "crop preserves raw nonsequential mixed basis and original references" {
  let values = [0, 1, 2].map(p => {
    Array::makei(16, k => {
      @touchstone.complex(
        (p * 16 + k + 1).to_double() / 256.0,
        im=-k.to_double() / 512.0,
      )
    })
  })
  let modes = ["C3,4", "D1,2", "D3,4", "C1,2"]
  let doc = @touchstone.document(
    @touchstone.network(4, [1.0e6, 3.0e6, 5.0e6], values, [
      50.0, 50.0, 75.0, 75.0,
    ]),
    mixed_mode_order=modes,
    noise_reference_ohms=40.0,
    information=["raw modal samples"],
  )
  let cropped = doc.crop(3.0e6, 3.0e6)
  assert_eq(cropped.mixed_mode_order(), modes)
  assert_eq(cropped.raw_network().reference_ohms(), [50.0, 50.0, 75.0, 75.0])
  assert_eq(cropped.modal_network().reference_ohms(), [37.5, 100.0, 150.0, 25.0])
  assert_eq(cropped.noise_reference_ohms(), 40.0)
  for k, z in cropped.raw_network().matrix(0) {
    assert_eq(z.re, (16 + k + 1).to_double() / 256.0)
    assert_eq(z.im, -k.to_double() / 512.0)
  }
}

///|
test "crop rejects nonfinite reversed negative bounds and empty intersections" {
  let doc = crop_test_document()
  for
    (start, end) in [
      (-1.0, 1000000.0),
      (2000000.0, 1000000.0),
      (0.0 / 0.0, 2000000.0),
      (0.0, 1.0 / 0.0),
      (6000000.0, 7000000.0),
    ] {
    try doc.crop(start, end) catch {
      _ => ()
    } noraise {
      _ => fail("invalid or empty crop accepted")
    }
  }
}

///|
test "crop new noise exclusion preserves the original legal noisy document" {
  let text = "[Version] 2.1\n# Hz S RI R 50\n[Number of Ports] 2\n[Two-Port Data Order] 12_21\n[Number of Frequencies] 2\n[Reference] 75 100\n[Number of Noise Frequencies] 1\n[Network Data]\n1000000 0 0 0 0 0.5 0 0 0\n2000000 0 0 0 0 0.25 0 0 0\n[Noise Data]\n0 0 0 0 25\n[End]\n"
  let doc = @touchstone.parse(text)
  let before = doc.write()
  assert_eq(doc.noise_data().length(), 1)
  try doc.crop(1000000.0, 2000000.0) catch {
    _ => ()
  } noraise {
    _ => fail("crop silently discarded noise")
  }
  assert_eq(doc.write(), before)
  let readback = @touchstone.parse(before)
  assert_eq(
    readback.noise_data().to_json().stringify(),
    doc.noise_data().to_json().stringify(),
  )
}
