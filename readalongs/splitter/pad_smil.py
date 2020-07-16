if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a SMIL file to a SVG file of its waveform, pitch, and units"
    )
    parser.add_argument("input_xml", type=str, help="Input XML file")
    parser.add_argument("input_smil", type=str, help="Input SMIL file")
    parser.add_argument(
        "padding",
        type=float,
        help="Duration (in seconds) to pad durations, when possible",
    )
    args = parser.parse_args()
    main(args.input_xml, args.input_smil)
