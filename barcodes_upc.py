"""
This module encodes and decodes barcodes as per UPC-A standards
"""
import zlib
import struct


class PoorMans1DBarCodeEncoderDecoder_UPC_A:
    """
    This class implements the UPC-A class of 2D barcode encoding and decoding via eps image.
    """
    PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
    PNG_IEND = tuple(map(lambda x: int.from_bytes(
        x, "big"), (b"\x49", b"\x45", b"\x4E", b"\x44")),)  # corresponds to b"IEND"
    PNG_IHDR = tuple(map(lambda x: int.from_bytes(
        x, "big"), (b"\x49", b"\x48", b"\x44", b"\x52")),)  # corresponds to b"IHDR"
    PNG_IDAT = tuple(map(lambda x: int.from_bytes(
        x, "big"), (b"\x49", b"\x44", b"\x41", b"\x54")),)  # corresponds to b"IDAT"

    def __init__(self,
                 width=1,  # Keep it an odd number
                 height=150,
                 left_odd_parities={
                     '0': '0001101', '1': '0011001', '2': '0010011', '3': '0111101', '4': '0100011',
                     '5': '0110001', '6': '0101111', '7': '0111011', '8': '0110111', '9': '0001011'},
                 right_even_parities={
                     '0': '1110010', '1': '1100110', '2': '1101100', '3': '1000010', '4': '1011100',
                     '5': '1001110', '6': '1010000', '7': '1000100', '8': '1001000', '9': '1110100'}):
        self.width = width
        self.height = height
        self.left_odd_parities = left_odd_parities
        self.right_even_parities = right_even_parities

    def create_ihdr(self, color_type: int = 0, bit_depth: int = 8, compression: int = 0,
                    filter_method: int = 0, interlace_method: int = 0, **kwargs) -> bytes:
        # Create the png header
        # First pack the Length
        block = struct.pack(
            "!BBBB", *tuple(map(lambda x: int.from_bytes(x, "big"), (b"\x00", b"\x00", b"\x00", b"\x0D")),))
        # Pack the type
        block += struct.pack(
            "!BBBB", *PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_IHDR)
        # Now pack the Data
        # Width calculations
        total_width = kwargs.get("barcode_width") or self.width
        # Header packing (The sequence must be honored)
        # Width -> Height -> BitDepth -> ColorSpace -> Compression-> Filter_Method -> Interlacing method
        block += struct.pack(
            "!I", total_width)
        block += struct.pack(
            "!I", self.height)
        block += struct.pack(
            "!B", bit_depth)
        block += struct.pack(
            "!B", color_type)
        block += struct.pack(
            "!B", compression)
        block += struct.pack(
            "!B", filter_method)
        block += struct.pack(
            "!B", interlace_method)
        crc_block = struct.pack("!I", zlib.crc32(block))
        return block + crc_block

    def create_iend(self) -> bytes:
        # Create IEND
        # First pack the Length
        block = struct.pack(
            "!BBBB", *tuple(map(lambda x: int.from_bytes(x, "big"), (b"\x00", b"\x00", b"\x00", b"\x00")),))
        # Pack the type
        block += struct.pack(
            "!BBBB", *PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_IEND)
        crc_block = struct.pack("!I", zlib.crc32(block))
        return block + crc_block

    def create_idat(self, data: list[list[bytes]]) -> bytes:
        # Create IDAT chunk
        block = struct.pack(
            "!BBBB", *PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_IDAT)
        # Go through data
        raw = b""
        for row in data:
            raw += b"\0"
            for column in row:
                # Ensure d is at max 255
                value = struct.pack("!B", column)
                raw += value
        # compress
        compressor = zlib.compressobj()
        compressed = compressor.compress(raw)
        compressed += compressor.flush()
        # Now write length
        length_block = struct.pack("!I", len(compressed))
        block += compressed
        crc_block = struct.pack("!I", zlib.crc32(block))
        return length_block + block + crc_block

    def create_png_file(self, data: list[bytes], **kwargs) -> bytes:
        # Create the png signature first
        png_returned = PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_SIGNATURE
        # Create header (IHDR)
        png_returned += self.create_ihdr(**kwargs)
        # Create data (IDAT)
        png_returned += self.create_idat(data)
        # Create end block (IEND)
        png_returned += self.create_iend()
        return png_returned

    def encode(self, number_to_encode: str):
        """
        Given a number in a string form, this method creates an eps image having the bar codes.
        """
        quiet_zone_left = 5*self.width  # Left quiet zone
        left_guard_width = 3*self.width  # Left guard is 101
        left_numbers_width = 7*6*self.width  # Left 6 numbers
        center_separator_width = 5*self.width  # Center separator is 01010
        right_numbers_width = 7*5*self.width  # Right 5 numbers
        right_guard_width = 3*self.width  # Right guard is 101
        check_sum_width = 7*1*self.width
        quiet_zone_right = 5*self.width  # Right quiet zone
        options_dict = {
            "barcode_width": quiet_zone_left + left_guard_width + left_numbers_width + center_separator_width + right_numbers_width + right_guard_width + check_sum_width + quiet_zone_right
        }
        data = []
        for _ in range(self.height):
            row = []
            # Write left quiet zone
            for _ in range(quiet_zone_left):
                for _ in range(self.width):
                    row.append(0)
            # Write left guard 101
            for digit in "101":
                for _ in range(self.width):
                    row.append(int(digit))
            # Write left 6 digits
            for digit in number_to_encode[:6:]:
                for number in self.left_odd_parities[digit]:
                    for _ in range(self.width):
                        row.append(int(number))
            # Write center separator
            for digit in "01010":
                for _ in range(self.width):
                    row.append(int(digit))
            # Write right 5 digits
            for digit in number_to_encode[6:-1:]:
                for number in self.right_even_parities[digit]:
                    for _ in range(self.width):
                        row.append(int(number))
            # Write checksum
            odd_sum = sum(map(lambda x: int(x)*3, number_to_encode[::2]))
            even_sum = sum(map(lambda x: int(x), number_to_encode[1:-1:2]))
            total_sum = odd_sum + even_sum
            mod_10 = total_sum % 10
            inverse_mod_10 = (10 - mod_10) % 10
            encoded_checksum = self.right_even_parities[str(inverse_mod_10)]
            for number in encoded_checksum:
                for _ in range(self.width):
                    row.append(int(number))
            # Write right guard 101
            for digit in "101":
                for _ in range(self.width):
                    row.append(int(digit))
            # Write right quiet zone
            for _ in range(quiet_zone_right):
                for _ in range(self.width):
                    row.append(0)
            # # invert since 0 means black and 1 means white
            row = [255 if x == 0 else 0 for x in row]
            data.append(row)
        # Transpose
        # data = list(zip(*data))
        # Create png file
        bytes_returned = self.create_png_file(data, **options_dict)
        with open(f"Barcode_{number_to_encode}.png", "wb") as filehandle:
            filehandle.write(bytes_returned)


if __name__ == "__main__":

    my_1_d_bar_obj = PoorMans1DBarCodeEncoderDecoder_UPC_A()
    my_1_d_bar_obj.encode("036000291452")
