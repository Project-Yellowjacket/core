import time

from machine import UART

from .utils.datetime import DateTime
from .utils.typing import Any, Sequence, TypeAlias, cast

_GLL = 0
_RMC = 1
_GGA = 2
_GSA = 3
_GSA_4_11 = 4
_GSV7 = 5
_GSV11 = 6
_GSV15 = 7
_GSV19 = 8
_RMC_4_1 = 9
_ST_MIN = _GLL
_ST_MAX = _RMC_4_1

_SENTENCE_PARAMS = (
    # 0 - _GLL
    "dcdcscC",
    # 1 - _RMC
    "scdcdcffsDCC",
    # 2 - _GGA
    "sdcdciiffsfsIS",
    # 3 - _GSA
    "ciIIIIIIIIIIIIfff",
    # 4 - _GSA_4_11
    "ciIIIIIIIIIIIIfffS",
    # 5 - _GSV7
    "iiiiiiI",
    # 6 - _GSV11
    "iiiiiiIiiiI",
    # 7 - _GSV15
    "iiiiiiIiiiIiiiI",
    # 8 - _GSV19
    "iiiiiiIiiiIiiiIiiiI",
    # 9 - _RMC_4_1
    "scdcdcffsDCCC",
)


# Internal helper parsing functions.
# These handle input that might be none or null and return none instead of
# throwing errors.
def _parse_degrees(nmea_data: str) -> int:
    # Parse a NMEA lat/long data pair 'dddmm.mmmm' into a pure degrees value.
    # Where ddd is the degrees, mm.mmmm is the minutes.
    if len(nmea_data) < 3:
        raise ValueError
    # To avoid losing precision handle degrees and minutes separately
    # Return the final value as an integer. Further functions can parse
    # this into a float or separate parts to retain the precision
    raw = nmea_data.split(".")
    degrees = int(raw[0]) // 100 * 1000000  # the ddd
    minutes = int(raw[0]) % 100  # the mm.
    minutes += int("{:0<4}".format(raw[1][:4])) / 10000
    minutes = int(minutes / 60 * 1000000)
    return degrees + minutes


def _parse_int(nmea_data: str) -> int:
    if nmea_data:
        return int(nmea_data)
    raise ValueError


def _parse_float(nmea_data: str) -> float:
    if nmea_data:
        return float(nmea_data)
    raise ValueError


def _read_degrees(data: list[float | str], index: int, neg: str) -> float:
    # This function loses precision with float32
    x = cast(float, data[index]) / 1000000
    if cast(str, data[index + 1]).lower() == neg:
        x = -x
    return x


def _read_int_degrees(data: list[float | str], index: int, neg: str) -> tuple[int, float]:
    deg = cast(int, data[index]) // 1000000
    minutes = cast(float, data[index]) % 1000000 / 10000
    if cast(str, data[index + 1]).lower() == neg:
        deg = -deg
    return (deg, minutes)


def _parse_talker(data_type: bytes) -> tuple[bytes, bytes]:
    # Split the data_type into talker and sentence_type
    if data_type[:1] == b"P":  # Proprietary codes
        return (data_type[:1], data_type[1:])

    return (data_type[:2], data_type[2:])
    """Parse sentence data for the specified sentence type and
    return a list of parameters in the correct format, or return None.
    """


def _parse_data(sentence_type: int, data: Sequence[str]) -> list[Any] | None:
    if not _ST_MIN <= sentence_type <= _ST_MAX:
        return None

    param_types = _SENTENCE_PARAMS[sentence_type]

    if len(param_types) != len(data):
        return None

    params: list[Any] = []
    try:
        for i, dti in enumerate(data):
            pti = param_types[i]
            len_dti = len(dti)
            nothing = not len_dti
            if pti == "c":
                if len_dti != 1:
                    return None
                params.append(dti)
            elif pti == "C":
                if nothing:
                    params.append(None)
                elif len_dti != 1:
                    return None
                else:
                    params.append(dti)
            elif pti == "d":
                params.append(_parse_degrees(dti))
            elif pti == "D":
                if nothing:
                    params.append(None)
                else:
                    params.append(_parse_degrees(dti))
            elif pti == "f":
                params.append(_parse_float(dti))
            elif pti == "i":
                params.append(_parse_int(dti))
            elif pti == "I":
                if nothing:
                    params.append(None)
                else:
                    params.append(_parse_int(dti))
            elif pti == "s":
                params.append(dti)
            elif pti == "S":
                if nothing:
                    params.append(None)
                else:
                    params.append(dti)
            else:
                raise TypeError("GPS: Unexpected parameter type {!r}".format(pti))
    except ValueError:
        return None

    return params


SatInfo: TypeAlias = "tuple[str, Any, Any, Any, int]"


class GPS:
    """GPS parsing module.  Can parse simple NMEA data sentences from serial
    GPS modules to read latitude, longitude, and more.
    """

    def __init__(self, uart: UART, debug: bool = False) -> None:
        self._uart = uart
        # Initialize null starting values for GPS attributes.
        self.latitude = None
        self.latitude_degrees = None
        self.latitude_minutes = None  # Use for full precision minutes
        self.longitude = None
        self.longitude_degrees = None
        self.longitude_minutes = None  # Use for full precision minutes
        self.fix_quality = 0
        self.fix_quality_3d = 0
        self.satellites = None
        self.satellites_prev = None
        self.horizontal_dilution = None
        self.altitude_m = None
        self.height_geoid = None
        self.speed_knots = None
        self.track_angle_deg = None
        self._sats: list[SatInfo] = []  # Temporary holder for information from GSV messages
        self.sats: dict[str, SatInfo] = {}  # Completed information from GSV messages
        self.isactivedata = None
        self.true_track = None
        self.mag_track = None
        self.sat_prns = None
        self.sel_mode = None
        self.pdop = None
        self.hdop = None
        self.vdop = None
        self.total_mess_num = None
        self.mess_num = None
        self._raw_sentence = None
        self._mode_indicator = None
        self._magnetic_variation = None
        self.debug = debug

    def update(self) -> bool:
        """Check for updated data from the GPS module and process it
        accordingly.  Returns True if new data was processed, and False if
        nothing new was received.
        """
        # Grab a sentence and check its data type to call the appropriate
        # parsing function.

        sentence = self._parse_sentence()
        if sentence is None:
            return False
        if self.debug:
            print(sentence)
        data_type, args = sentence
        if len(data_type) < 5:
            return False
        data_type = bytes(data_type.upper(), "ascii")
        (talker, sentence_type) = _parse_talker(data_type)

        # Check for all currently known GNSS talkers
        # GA - Galileo
        # GB - BeiDou Systems
        # GI - NavIC
        # GL - GLONASS
        # GP - GPS
        # GQ - QZSS
        # GN - GNSS / More than one of the above
        if talker not in {b"GA", b"GB", b"GI", b"GL", b"GP", b"GQ", b"GN"}:
            # It's not a known GNSS source of data
            # Assume it's a valid packet anyway
            return True

        result = True
        args = args.split(",")
        if sentence_type == b"GLL":  # Geographic position - Latitude/Longitude
            result = self._parse_gll(args)
        elif sentence_type == b"RMC":  # Minimum location info
            result = self._parse_rmc(args)
        elif sentence_type == b"GGA":  # 3D location fix
            result = self._parse_gga(args)
        elif sentence_type == b"GSV":  # Satellites in view
            result = self._parse_gsv(talker, args)
        elif sentence_type == b"GSA":  # GPS DOP and active satellites
            result = self._parse_gsa(talker, args)

        return result

    def send_command(self, command: bytes, add_checksum: bool = True) -> None:
        """Send a command string to the GPS.  If add_checksum is True (the
        default) a NMEA checksum will automatically be computed and added.
        Note you should NOT add the leading $ and trailing * to the command
        as they will automatically be added!
        """
        self.write(b"$")
        self.write(command)
        if add_checksum:
            checksum = 0
            for char in command:
                checksum ^= char
            self.write(b"*")
            self.write("{:02X}".format(checksum).encode("ascii"))
        self.write(b"\r\n")

    @property
    def has_fix(self) -> bool:
        """True if a current fix for location information is available."""
        return self.fix_quality is not None and self.fix_quality >= 1

    @property
    def has_3d_fix(self) -> bool:
        """Returns true if there is a 3d fix available.
        use has_fix to determine if a 2d fix is available,
        passing it the same data"""
        return self.fix_quality_3d is not None and self.fix_quality_3d >= 2

    @property
    def datetime(self) -> DateTime:
        """Return datetime object to feed rtc.set_time_source() function"""
        return self.timestamp_utc

    @property
    def nmea_sentence(self) -> str | None:
        """Return raw_sentence which is the raw NMEA sentence read from the GPS"""
        return self._raw_sentence

    def read(self, num_bytes: int) -> bytes | None:
        """Read up to num_bytes of data from the GPS directly, without parsing.
        Returns a bytestring with up to num_bytes or None if nothing was read"""
        return self._uart.read(num_bytes)

    def write(self, bytestr: bytes) -> int | None:
        """Write a bytestring data to the GPS directly, without parsing
        or checksums"""
        return self._uart.write(bytestr)

    @property
    def in_waiting(self) -> int:
        """Returns number of bytes available in UART read buffer"""
        return self._uart.any()

    def readline(self) -> bytes | None:
        """Returns a newline terminated bytestring, must have timeout set for
        the underlying UART or this will block forever!"""
        return self._uart.readline()

    def _read_sentence(self) -> str | None:
        # Parse any NMEA sentence that is available.
        # This needs to be refactored when it can be tested.

        # Only continue if we have at least 11 bytes in the input buffer
        if self.in_waiting < 11:
            return None

        sentence = self.readline()
        if not sentence:
            return None
        try:
            sentence = str(sentence, "ascii").strip()
        except UnicodeError:
            return None
        # Look for a checksum and validate it if present.
        if len(sentence) > 7 and sentence[-3] == "*":
            # Get included checksum, then calculate it and compare.
            expected = int(sentence[-2:], 16)
            actual = 0
            for i in range(1, len(sentence) - 3):
                actual ^= ord(sentence[i])
            if actual != expected:
                return None  # Failed to validate checksum.

            # copy the raw sentence
            self._raw_sentence = sentence

            return sentence
        # At this point we don't have a valid sentence
        return None

    def _parse_sentence(self) -> tuple[str, str] | None:
        sentence = self._read_sentence()

        # sentence is a valid NMEA with a valid checksum
        if sentence is None:
            return None

        # Remove checksum once validated.
        sentence = sentence[:-3]
        # Parse out the type of sentence (first string after $ up to comma)
        # and then grab the rest as data within the sentence.
        delimiter = sentence.find(",")
        if delimiter == -1:
            return None  # Invalid sentence, no comma after data type.
        data_type = sentence[1:delimiter]
        return (data_type, sentence[delimiter + 1 :])

    def _update_timestamp_utc(self, time_utc: str, date: str | None = None) -> None:
        hours = int(time_utc[:2])
        mins = int(time_utc[2:4])
        secs = int(time_utc[4:6])
        if date is None:
            if not hasattr(self, "timestamp_utc"):
                day, month, year = 0, 0, 0
            else:
                day = self.timestamp_utc.day
                month = self.timestamp_utc.month
                year = self.timestamp_utc.year
        else:
            day = int(date[:2])
            month = int(date[2:4])
            year = 2000 + int(date[4:6])

        self.timestamp_utc = DateTime(year, month, day, hours, mins, secs)

    def _parse_gll(self, data_: list[str]) -> bool:
        # GLL - Geographic Position - Latitude/Longitude

        if len(data_) != 7:
            return False  # Unexpected number of params.
        data = _parse_data(_GLL, data_)
        if data is None:
            return False  # Params didn't parse

        self._parse_coords(data, 0, 2)
        # UTC time of position
        self._update_timestamp_utc(data[4])

        # Status Valid(A) or Invalid(V)
        self.isactivedata = data[5]

        # Parse FAA mode indicator
        self._mode_indicator = data[6]

        return True

    def _parse_rmc(self, data_: list[str]) -> bool:
        # RMC - Recommended Minimum Navigation Information

        if len(data_) not in {12, 13}:
            return False  # Unexpected number of params.
        data = _parse_data({12: _RMC, 13: _RMC_4_1}[len(data_)], data_)
        if data is None:
            self.fix_quality = 0
            return False  # Params didn't parse

        # UTC time of position and date
        self._update_timestamp_utc(data[0], data[8])

        # Status Valid(A) or Invalid(V)
        self.isactivedata = data[1]
        if data[1].lower() == "a":
            if self.fix_quality == 0:
                self.fix_quality = 1
        else:
            self.fix_quality = 0

        self._parse_coords(data, 2, 4)
        # Speed over ground, knots
        self.speed_knots = data[6]

        # Track made good, degrees true
        self.track_angle_deg = data[7]

        # Magnetic variation
        if data[9] is None or data[10] is None:
            self._magnetic_variation = None
        else:
            self._magnetic_variation = _read_degrees(data, 9, "w")

        # Parse FAA mode indicator
        self._mode_indicator = data[11]

        return True

    def _parse_gga(self, data_: list[str]) -> bool:
        # GGA - Global Positioning System Fix Data

        if len(data_) != 14:
            return False  # Unexpected number of params.
        data = _parse_data(_GGA, data_)
        if data is None:
            self.fix_quality = 0
            return False  # Params didn't parse

        # UTC time of position
        self._update_timestamp_utc(data[0])

        self._parse_coords(data, 1, 3)
        # GPS quality indicator
        # 0 - fix not available,
        # 1 - GPS fix,
        # 2 - Differential GPS fix (values above 2 are 2.3 features)
        # 3 - PPS fix
        # 4 - Real Time Kinematic
        # 5 - Float RTK
        # 6 - estimated (dead reckoning)
        # 7 - Manual input mode
        # 8 - Simulation mode
        self.fix_quality = data[5]

        # Number of satellites in use, 0 - 12
        self.satellites = data[6]

        # Horizontal dilution of precision
        self.horizontal_dilution = data[7]

        # Antenna altitude relative to mean sea level
        self.altitude_m = _parse_float(data[8])
        # data[9] - antenna altitude unit, always 'M' ???

        # Geoidal separation relative to WGS 84
        self.height_geoid = _parse_float(data[10])
        # data[11] - geoidal separation unit, always 'M' ???

        # data[12] - Age of differential GPS data, can be null
        # data[13] - Differential reference station ID, can be null

        return True

    def _parse_coords(self, data: list[float | str], idx_1: int, idx_2: int):
        self.latitude = _read_degrees(data, idx_1, "s")
        self.latitude_degrees, self.latitude_minutes = _read_int_degrees(data, idx_1, "s")
        self.longitude = _read_degrees(data, idx_2, "w")
        self.longitude_degrees, self.longitude_minutes = _read_int_degrees(data, idx_2, "w")

    def _parse_gsa(self, talker_: bytes, data_: list[str]) -> bool:
        # GSA - GPS DOP and active satellites

        if len(data_) not in {17, 18}:
            return False  # Unexpected number of params.
        data = _parse_data({17: _GSA, 18: _GSA_4_11}[len(data_)], data_)
        if data is None:
            self.fix_quality_3d = 0
            return False  # Params didn't parse

        talker = talker_.decode("ascii")

        # Selection mode: 'M' - manual, 'A' - automatic
        self.sel_mode = data[0]

        # Mode: 1 - no fix, 2 - 2D fix, 3 - 3D fix
        self.fix_quality_3d = data[1]

        satlist = list(filter(None, data[2:-4]))
        self.sat_prns = ["{}{}".format(talker, sat) for sat in satlist]
        # PDOP, dilution of precision
        self.pdop = _parse_float(data[14])

        # HDOP, horizontal dilution of precision
        self.hdop = _parse_float(data[15])

        # VDOP, vertical dilution of precision
        self.vdop = _parse_float(data[16])

        # data[17] - System ID

        return True

    def _parse_gsv(self, talker: bytes, data_: list[str]) -> bool:
        # GSV - Satellites in view

        if len(data_) not in {7, 11, 15, 19}:
            return False  # Unexpected number of params.
        data = _parse_data(
            {7: _GSV7, 11: _GSV11, 15: _GSV15, 19: _GSV19}[len(data_)],
            data_,
        )
        if data is None:
            return False  # Params didn't parse

        talker_ = talker.decode("ascii")

        # Number of messages
        self.total_mess_num = data[0]
        # Message number
        self.mess_num = data[1]
        # Number of satellites in view
        self.satellites = data[2]

        sat_tup = data[3:]

        timestamp = time.ticks_ms()

        self._sats += (
            (
                "{}{}".format(talker_, sat_tup[0 + j]),
                sat_tup[1 + j],
                sat_tup[2 + j],
                sat_tup[3 + j],
                timestamp,
            )
            for j in range(0, len(sat_tup) // 4, 4)
        )

        if self.mess_num == self.total_mess_num:
            # Last part of GSV message
            if len(self._sats) == self.satellites:
                # Transfer received satellites to self.sats
                # Remove all satellites which haven't
                # been seen for 30 seconds
                timestamp = time.ticks_ms()
                for i, sat in self.sats.items():
                    if time.ticks_diff(timestamp, sat[4]) > 30_000:
                        del self.sats[i]
                for sat in self._sats:
                    self.sats[sat[0]] = sat
            self._sats.clear()

        self.satellites_prev = self.satellites

        return True
