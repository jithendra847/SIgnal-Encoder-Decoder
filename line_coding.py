"""Digital line coding schemes that map bits to voltage levels.

Voltage levels:
    +1 represents +1 V
    -1 represents -1 V
     0 represents  0 V

Manchester schemes produce two voltage levels per input bit.
The other schemes produce one voltage level per input bit.
"""

from __future__ import annotations

from collections.abc import Callable

from data_generator import validate_binary_data


def encode_nrz_l(data: str) -> list[int]:
    """Encode NRZ-L: 0 = +1 V and 1 = -1 V."""

    # Validate the input so the encoder receives only binary data.
    bits = validate_binary_data(data)

    # NRZ-L uses a fixed voltage for each bit:
    # 0 -> +1 V, 1 -> -1 V.
    # The voltage does not depend on the previous bit.
    return [1 if bit == "0" else -1 for bit in bits]


def encode_nrz_i(data: str, initial_level: int = 1) -> list[int]:
    """Encode NRZ-I; each 1 changes level at the bit's start.

    initial_level is the voltage immediately before the first bit.
    """

    bits = validate_binary_data(data)
    _validate_initial_level(initial_level)

    # Keep track of the current voltage level.
    level = initial_level
    levels: list[int] = []

    for bit in bits:
        if bit == "1":
            # A 1 causes a transition: +1 becomes -1, or vice versa.
            level *= -1

        # A 0 leaves the voltage unchanged.
        # Store the resulting voltage for this bit.
        levels.append(level)

    return levels


def encode_manchester(data: str) -> list[int]:
    """Encode Manchester: 0 = [+1, -1], 1 = [-1, +1]."""

    bits = validate_binary_data(data)
    levels: list[int] = []

    for bit in bits:
        # Each bit is represented by two half-bit voltage levels.
        # The middle transition is present for both 0 and 1.
        if bit == "0":
            levels.extend((1, -1))
        else:
            levels.extend((-1, 1))

    return levels


def encode_differential_manchester(
    data: str, initial_level: int = 1
) -> list[int]:
    """Encode Differential Manchester.

    Every bit has a middle transition.
    A 0 also transitions at the beginning; a 1 does not.
    """

    bits = validate_binary_data(data)
    _validate_initial_level(initial_level)

    # This level represents the voltage immediately before the current bit.
    level = initial_level
    levels: list[int] = []

    for bit in bits:
        if bit == "0":
            # A zero requires a transition at the start of the bit.
            level *= -1

        # Record the first half of the bit.
        levels.append(level)

        # Every bit must transition halfway through the bit,
        # regardless of whether the input bit is 0 or 1.
        level *= -1

        # Record the second half of the bit.
        levels.append(level)

    return levels


def encode_ami(data: str, initial_pulse: int = 1) -> list[int]:
    """Encode AMI: zero = 0 V; successive one pulses alternate polarity.

    initial_pulse determines the polarity of the first 1 pulse.
    """

    bits = validate_binary_data(data)
    _validate_initial_level(initial_pulse)

    # Start with the opposite polarity so that the first 1 pulse
    # takes the requested initial_pulse polarity.
    pulse = -initial_pulse
    levels: list[int] = []

    for bit in bits:
        if bit == "0":
            # A zero is transmitted as zero voltage.
            # It does not change the polarity of the next 1 pulse.
            levels.append(0)
        else:
            # Every 1 pulse must have the opposite polarity
            # from the previous 1 pulse.
            pulse *= -1
            levels.append(pulse)

    return levels


# Map each scheme name to its encoder function.
# This avoids a long if/elif chain when selecting an encoder.
_ENCODERS: dict[str, Callable[..., list[int]]] = {
    "nrz-l": encode_nrz_l,
    "nrz-i": encode_nrz_i,
    "manchester": encode_manchester,
    "differential-manchester": encode_differential_manchester,
    "ami": encode_ami,
}


def encode_line_code(
    data: str,
    scheme: str,
    *,
    initial_level: int = 1,
) -> list[int]:
    """Encode bits using a scheme name and return voltage levels.

    Scheme names are case-insensitive. The initial level is used by
    NRZ-I and Differential Manchester; for AMI, it determines
    the polarity of the first 1 pulse.
    """

    # Normalize names so inputs such as "NRZ_I", "nrz-i",
    # and "NRZ I" can select the same encoder.
    normalized = scheme.strip().lower().replace("_", "-").replace(" ", "-")

    # Look up the appropriate encoder using the scheme name.
    try:
        encoder = _ENCODERS[normalized]
    except (AttributeError, KeyError) as error:
        names = ", ".join(_ENCODERS)

        # Report the available schemes if the name is invalid.
        raise ValueError(
            f"unknown scheme {scheme!r}; choose one of: {names}"
        ) from error

    # These encoders need the initial voltage or pulse polarity.
    if normalized in {"nrz-i", "differential-manchester", "ami"}:
        return encoder(data, initial_level)

    # NRZ-L and Manchester do not need an initial voltage.
    return encoder(data)


def _validate_initial_level(level: int) -> None:
    """Ensure an initial voltage level is either +1 V or -1 V."""

    # Reject booleans too, because Python treats True as 1 and False as 0.
    if isinstance(level, bool) or not isinstance(level, int) or level not in (-1, 1):
        raise ValueError("initial level must be +1 or -1")