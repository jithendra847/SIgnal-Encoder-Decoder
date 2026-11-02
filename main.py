"""Interactive entry point for the data communication assignment."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from data_generator import (
    generate_data_with_eight_zeros,
    generate_data_with_four_zeros,
    generate_random_bits,
    longest_zero_run,
    validate_binary_data,
)
from decoder import decode_waveform_image
from line_coding import encode_line_code
from modulation import delta_decode, delta_encode, pcm_decode, pcm_encode
from palindrome import longest_palindrome
from plotter import (
    plot_delta_reconstruction,
    plot_pcm_reconstruction,
    plot_waveform,
)
from scrambling import encode_b8zs, encode_hdb3


LINE_SCHEMES = {
    "1": ("NRZ-L", "nrz-l", 1),
    "2": ("NRZ-I", "nrz-i", 1),
    "3": ("Manchester", "manchester", 2),
    "4": ("Differential Manchester", "differential-manchester", 2),
    "5": ("AMI", "ami", 1),
}

SCRAMBLERS = {
    "1": ("B8ZS", encode_b8zs, "b8zs"),
    "2": ("HDB3", encode_hdb3, "hdb3"),
}


def run_interactive(
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], object] | None = None,
) -> None:
    """Run the interactive program; optional I/O functions simplify testing."""
    ask = input if input_fn is None else input_fn
    show = print if output_fn is None else output_fn
    show("Data Communication Encoder and Decoder")
    show("1. Digital input\n2. Analog input")

    try:
        mode = ask("Choose input type (1 or 2): ").strip()
        workflows = {"1": run_digital_workflow, "2": run_analog_workflow}
        workflow = workflows.get(mode)
        if workflow is None:
            raise ValueError("Choose 1 for digital input or 2 for analog input.")
        workflow(ask, show)
    except (TypeError, ValueError, ImportError, OSError) as error:
        show(f"Unable to complete this operation: {error}")


def run_digital_workflow(ask: Callable[[str], str], show: Callable[[str], object]) -> None:
    """Generate or accept bits, optionally inspect them, then line-code them."""
    bits = _get_digital_data(ask, show)
    show(f"Digital data: {bits}")
    show(f"Longest consecutive zero run: {longest_zero_run(bits)}")

    if _yes_no(ask("Find the longest palindrome in these bits? (y/n): ")):
        result = longest_palindrome(bits)
        show(
            f"Longest palindrome: {result.substring!r}; length {result.length}; "
            f"starting index {result.start_index}."
        )

    _offer_line_coding(bits, ask, show)


def run_analog_workflow(ask: Callable[[str], str], show: Callable[[str], object]) -> None:
    """Encode analog samples with PCM or Delta Modulation and plot output."""
    show("1. PCM\n2. Delta Modulation")
    choice = ask("Choose modulation (1 or 2): ").strip()
    samples = _read_analog_samples(ask)

    if choice == "1":
        bits_per_sample = _read_int(ask, "Bits per PCM sample [8]: ", default=8)
        minimum = _read_float(ask, "Quantizer minimum [-1]: ", default=-1.0)
        maximum = _read_float(ask, "Quantizer maximum [1]: ", default=1.0)
        digital_stream = pcm_encode(samples, bits_per_sample, minimum, maximum)
        reconstruction = pcm_decode(digital_stream, bits_per_sample, minimum, maximum)
        path = _read_path(ask, "PCM staircase image path [pcm_reconstruction.png]: ", "pcm_reconstruction.png")
        plot_pcm_reconstruction(reconstruction, path)
        show(f"PCM digital stream: {digital_stream}")
        show(f"PCM reconstruction saved to: {path}")
    elif choice == "2":
        step_size = _read_float(ask, "Positive Delta Modulation step size: ")
        initial_value = _read_float(ask, "Initial reconstruction value [0]: ", default=0.0)
        digital_stream = delta_encode(samples, step_size, initial_value)
        reconstruction = delta_decode(digital_stream, step_size, initial_value)
        path = _read_path(
            ask, "Delta staircase image path [delta_reconstruction.png]: ",
            "delta_reconstruction.png",
        )
        plot_delta_reconstruction(reconstruction, path)
        show(f"Delta Modulation digital stream: {digital_stream}")
        show(f"Delta Modulation reconstruction saved to: {path}")
    else:
        raise ValueError("Choose 1 for PCM or 2 for Delta Modulation.")

    if _yes_no(ask("Pass this digital stream to a line-coding scheme? (y/n): ")):
        _offer_line_coding(digital_stream, ask, show)


def _get_digital_data(ask: Callable[[str], str], show: Callable[[str], object]) -> str:
    show("Digital data source:")
    show("1. Random bits\n2. Include four consecutive zeros\n3. Include eight consecutive zeros\n4. Enter bits")
    choice = ask("Choose a source (1-4): ").strip()
    if choice == "4":
        bits = validate_binary_data(ask("Enter binary data: ").strip())
        if not bits:
            raise ValueError("Enter at least one bit.")
        return bits

    generators = {
        "1": generate_random_bits,
        "2": generate_data_with_four_zeros,
        "3": generate_data_with_eight_zeros,
    }
    generator = generators.get(choice)
    if generator is None:
        raise ValueError("Choose a data source from 1 to 4.")
    length = _read_int(ask, "Number of bits to generate: ")
    if length < 1:
        raise ValueError("Number of bits must be positive.")
    return generator(length)


def _offer_line_coding(
    bits: str, ask: Callable[[str], str], show: Callable[[str], object]
) -> None:
    show("Line-coding schemes:")
    show("1. NRZ-L\n2. NRZ-I\n3. Manchester\n4. Differential Manchester\n5. AMI")
    selection = ask("Choose a scheme (1-5): ").strip()
    try:
        label, scheme, samples_per_bit = LINE_SCHEMES[selection]
    except KeyError as error:
        raise ValueError("Choose a line-coding scheme from 1 to 5.") from error

    initial_level = 1
    if scheme in {"nrz-i", "differential-manchester", "ami"}:
        initial_level = _read_int(ask, "Initial reference/pulse level (+1 or -1) [1]: ", default=1)
        if initial_level not in (-1, 1):
            raise ValueError("Initial reference/pulse level must be +1 or -1.")

    scrambling = None
    if scheme == "ami" and _yes_no(ask("Apply B8ZS or HDB3 scrambling? (y/n): ")):
        show("1. B8ZS\n2. HDB3")
        choice = ask("Choose scrambling (1 or 2): ").strip()
        try:
            scrambling_label, scrambler, scrambling = SCRAMBLERS[choice]
        except KeyError as error:
            raise ValueError("Choose 1 for B8ZS or 2 for HDB3.") from error
        levels = scrambler(bits, initial_level)
        label = f"AMI with {scrambling_label}"
    else:
        levels = encode_line_code(bits, scheme, initial_level=initial_level)

    waveform_path = _read_path(ask, "Waveform image path [waveform.png]: ", "waveform.png")
    plot_waveform(
        levels,
        waveform_path,
        scheme=label,
        samples_per_bit=samples_per_bit,
        bit_count=len(bits),
    )
    show(f"Encoded voltage levels: {levels}")
    show(f"Waveform saved to: {waveform_path}")

    if _yes_no(ask("Decode the saved waveform image? (y/n): ")):
        decoded = decode_waveform_image(
            waveform_path,
            "ami" if scrambling else scheme,
            len(bits),
            samples_per_bit=samples_per_bit,
            initial_level=initial_level,
            scrambling=scrambling,
        )
        show(f"Decoded bits: {decoded}")
        show(f"Decoded data matches input: {decoded == bits}")


def _read_analog_samples(ask: Callable[[str], str]) -> list[float]:
    text = ask("Enter analog samples separated by commas (for example: -0.5, 0, 0.7): ")
    try:
        samples = [float(part.strip()) for part in text.split(",") if part.strip()]
    except ValueError as error:
        raise ValueError("Samples must be numbers separated by commas.") from error
    if not samples:
        raise ValueError("Enter at least one analog sample.")
    return samples


def _read_int(
    ask: Callable[[str], str], prompt: str, *, default: int | None = None
) -> int:
    raw = ask(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError("Enter a whole number.") from error


def _read_float(
    ask: Callable[[str], str], prompt: str, *, default: float | None = None
) -> float:
    raw = ask(prompt).strip()
    if not raw and default is not None:
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError("Enter a number.") from error


def _read_path(
    ask: Callable[[str], str], prompt: str, default: str
) -> Path:
    raw = ask(prompt).strip()
    return Path(raw or default)


def _yes_no(answer: str) -> bool:
    normalized = answer.strip().lower()
    if normalized not in {"y", "yes", "n", "no"}:
        raise ValueError("Please answer y or n.")
    return normalized in {"y", "yes"}


def main() -> None:
    """Launch the assignment's interactive workflow."""
    run_interactive()


if __name__ == "__main__":
    main()
