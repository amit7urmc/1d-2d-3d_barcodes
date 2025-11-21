"""
This module encodes and decodes EAN-13 series of barcodes.
https://en.wikipedia.org/wiki/International_Article_Number
"""

import zlib
import struct
import hashlib

from barcodes_upc import PoorMans1DBarCodeEncoderDecoder_UPC_A


class PoorMans1DBarCodeEncoderDecoder_EAN_13(PoorMans1DBarCodeEncoderDecoder_UPC_A):
    """
    This class implements EAN-13 standard 1D bar codes.
    """

    def __init__(self,
                 width=3,
                 height=150,
                 upper_quiet_zone=10,
                 lower_quiet_zone=10,
                 left_quiet_zone_width=5,
                 right_quiet_zone_width=3,
                 left_odd_parities={
                     '0': '0001101', '1': '0011001', '2': '0010011', '3': '0111101', '4': '0100011',
                     '5': '0110001', '6': '0101111', '7': '0111011', '8': '0110111', '9': '0001011'},
                 g_parities={
                     '0': '0100111', '1': '0110011', '2': '0011011', '3': '0100001', '4': '0011101',
                     '5': '0111001', '6': '0000101', '7': '0010001', '8': '0001111', '9': '0100101'},
                 right_even_parities={
                     '0': '1110010', '1': '1100110', '2': '1101100', '3': '1000010', '4': '1011100',
                     '5': '1001110', '6': '1010000', '7': '1000100', '8': '1001000', '9': '1110100'},
                 structure_first_digit={
                     '0': 'LLLLLLRRRRRR', '1': 'LLGLGGRRRRRR', '2': 'LLGGLGRRRRRR', '3': 'LLGGGLRRRRRR',
                     '4': 'LGLLGGRRRRRR', '5': 'LGGLLGRRRRRR', '6': 'LGGLLGRRRRRR', '7': 'LGLGLGRRRRRR',
                     '8': 'LGLGGLRRRRRR', '9': 'LGGLGLRRRRRR'}):
        super().__init__(width=width,
                         height=height,
                         upper_quiet_zone=upper_quiet_zone,
                         lower_quiet_zone=lower_quiet_zone,
                         left_quiet_zone_width=left_quiet_zone_width,
                         right_quiet_zone_width=right_quiet_zone_width,
                         left_odd_parities=left_odd_parities,
                         right_even_parities=right_even_parities)
        self.g_parities = g_parities
        self.structure_first_digit = structure_first_digit

    def encode(self, number_to_encode: str):
        """
        Given a number in a string form, this method creates an eps image having the bar codes.
        """
        quiet_zone_left = self.left_quiet_zone_width*self.width  # Left quiet zone
        left_guard_width = 3*self.width  # Left guard is 101
        left_numbers_width = 7*6*self.width  # Left 6 numbers
        center_separator_width = 5*self.width  # Center separator is 01010
        right_numbers_width = 7*5*self.width  # Right 5 numbers
        right_guard_width = 3*self.width  # Right guard is 101
        check_sum_width = 7*1*self.width
        quiet_zone_right = self.right_quiet_zone_width*self.width  # Right quiet zone
        options_dict = {
            "barcode_width": quiet_zone_left +
            left_guard_width +
            left_numbers_width +
            center_separator_width +
            right_numbers_width +
            right_guard_width +
            check_sum_width +
            quiet_zone_right
        }
        data = []
        data_structure_needed = self.structure_first_digit[number_to_encode[0]]
        sequence_to_use = [
            self.left_odd_parities if x == "L" else self.g_parities if x == "G" else self.right_even_parities
            for x in data_structure_needed
        ]
        for i in range(self.upper_quiet_zone):
            data.append([255]*options_dict["barcode_width"])
        for _ in range(self.height-self.upper_quiet_zone-self.lower_quiet_zone):
            row = []
            # Write left quiet zone
            for _ in range(self.left_quiet_zone_width):
                for _ in range(self.width):
                    row.append(0)
            # Write left guard 101
            for digit in "101":
                for _ in range(self.width):
                    row.append(int(digit))
            # Write left 6 digits
            for index_l, digit in enumerate(number_to_encode[1:7:]):
                # print("left", index_l, sequence_to_use[index_l][digit])
                for number in sequence_to_use[index_l][digit]:
                    for _ in range(self.width):
                        row.append(int(number))
            # Write center separator
            for digit in "01010":
                for _ in range(self.width):
                    row.append(int(digit))
            # Write right 6 digits
            for index_r, digit in enumerate(number_to_encode[7:12:], start=6):
                # print("right", index_r, sequence_to_use[index_r][digit])
                for number in sequence_to_use[index_r][digit]:
                    for _ in range(self.width):
                        row.append(int(number))
            # Write checksum
            odd_sum = sum(map(lambda x: int(x)*3, number_to_encode[-1:1:-2]))
            even_sum = sum(map(lambda x: int(x), number_to_encode[-2:1:-2]))
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
            for _ in range(self.right_quiet_zone_width):
                for _ in range(self.width):
                    row.append(0)
            # # invert since 0 means black and 1 means white
            row = [255 if x == 0 else 0 for x in row]
            data.append(row)
            # Append row
        for i in range(self.lower_quiet_zone):
            data.append([255]*options_dict["barcode_width"])
        # Create png file
        bytes_returned = self.create_png_file(data, **options_dict)
        with open(f"Barcode_ean_13_{number_to_encode}-{inverse_mod_10}.png", "wb") as filehandle:
            filehandle.write(bytes_returned)

    def decode(self, png_image_to_read: bytes, verbose: bool = False) -> str:
        """
        This method decodes the png image into the number.
        The URL https://pyokagan.name/blog/2019-10-14-png/ has been used as a starting reference
        """
        # Read the signature first
        with open(png_image_to_read, "rb") as filehandle:
            current_line = filehandle.read(
                len(PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_SIGNATURE))
            if current_line != PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_SIGNATURE:
                if verbose:
                    print("This is not a png file!")
                raise TypeError("This is not a png file!")
            if verbose:
                print("This is a png file!")

            # Now get the IHDR block
            ihdr_length = struct.unpack("!4B", filehandle.read(4))[0]
            type_ = struct.unpack("!4B", filehandle.read(4))
            if type_ != PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_IHDR:
                if verbose:
                    print("This is not an IHDR block!")
                raise TypeError("This is not an IHDR block!")
            if verbose:
                print("This is an IHDR block!")
            data = struct.unpack("!IIBBBBB", filehandle.read(13))
            width, height, bit_depth, color_type, compression, filter_method, interlace_method = data
            if verbose:
                print(
                    f"{width=}, {height=}, {bit_depth=}, {color_type=}, {compression=}, {filter_method=}, {interlace_method=}")

            # Check CRC for this block
            saved_checksum = struct.unpack("!I", filehandle.read(4))[0]
            computed_checksum = zlib.crc32(
                struct.pack("!BBBBIIBBBBB", *type_, *data))
            if saved_checksum != computed_checksum:
                if verbose:
                    print(
                        f"IHDR Checksum failed! Saved was {saved_checksum} and computed was {computed_checksum}")
                raise TypeError("Checksum failed!")
            if verbose:
                print("IHDR Checksum passed!")

            # Now get the IDAT block
            idat_length = struct.unpack("!I", filehandle.read(4))[0]
            type_ = struct.unpack("!4B", filehandle.read(4))
            if type_ != PoorMans1DBarCodeEncoderDecoder_UPC_A.PNG_IDAT:
                if verbose:
                    print("This is not an IDAT block!")
                raise TypeError("This is not an IDAT block!")
            if verbose:
                print("This is an IDAT block!")

            # The CRC is calculated on the chunk type and the chunk data
            chunk_type_and_data = struct.pack(
                "!4B", *type_) + filehandle.read(idat_length)
            decompressed_data = zlib.decompress(chunk_type_and_data[4:])

            saved_checksum = struct.unpack("!I", filehandle.read(4))[0]
            computed_checksum = zlib.crc32(chunk_type_and_data)

            if saved_checksum != computed_checksum:
                if verbose:
                    print(
                        f"IDAT checksum failed! Saved was {saved_checksum} and computed was {computed_checksum}")
                raise TypeError("Checksum failed!")
            if verbose:
                print("IDAT Checksum passed!")

            data_block_ = [decompressed_data[i+1:i+width+1]
                           for i in range(0, len(decompressed_data), width+1)]

            # Quick check all rows are same/redundant so that we can just focus on 1st scanline apart from the upper and lower quiet zone
            m = hashlib.sha1()
            m.update(data_block_[self.upper_quiet_zone:-
                     self.lower_quiet_zone][0])
            first_row_checksum = m.hexdigest()
            for row_index, row in enumerate(data_block_[self.upper_quiet_zone:-self.lower_quiet_zone]):
                m1 = hashlib.sha1()
                m1.update(row)
                if m1.hexdigest() != first_row_checksum:
                    raise ValueError(
                        f"Something strange. We were expecting all rows to be same but at least index {row_index} is different!")
            data_block = []
            for row in data_block_:
                data_block.append([int(x) for x in row])
            # Remove the upper quiet zone
            data_block = data_block[self.upper_quiet_zone:-
                                    self.lower_quiet_zone]

            relevant_data = data_block[0]
            # Get left quiet zone
            left_quiet_zone = relevant_data[:
                                            self.left_quiet_zone_width*self.width]
            if any(map(lambda x: x != 255, left_quiet_zone)):
                raise ValueError("Identification of left quiet zone failed")
            relevant_data = relevant_data[self.left_quiet_zone_width*self.width:]
            # Get left guard
            left_guard = relevant_data[:3*self.width]
            if left_guard != [0]*self.width + [255]*self.width + [0]*self.width:
                raise ValueError("Identification of left guard failed")
            relevant_data = relevant_data[3*self.width:]
            # Get left 6 digits
            left_numbers = relevant_data[:6*7*self.width]
            numbers_read = []
            reverse_left_odd_parities = {v: k for k,
                                         v in self.left_odd_parities.items()}
            revers_g_parities = {v: k for k,
                                 v in self.g_parities.items()}
            parities = ""
            for i in range(6):
                read_key = ""
                for j in range(7):
                    chunk = left_numbers[:self.width]
                    if chunk == [0]*self.width:
                        read_key += "1"
                    else:
                        read_key += "0"
                    left_numbers = left_numbers[self.width:]
                if read_key in reverse_left_odd_parities:
                    numbers_read.append(
                        reverse_left_odd_parities.get(read_key))
                    parities += "L"
                elif read_key in revers_g_parities:
                    numbers_read.append(revers_g_parities.get(read_key))
                    parities += "G"
                else:
                    raise ValueError(
                        "No matching parity as per expectation found")
            # Now get the first digit based on parities pattern
            reverse_structure_first_digit = {v[:6]: k for k,
                                             v in self.structure_first_digit.items()}
            first_digit = reverse_structure_first_digit.get(parities)
            if not first_digit:
                raise ValueError("Identification of first digit failed")
            numbers_read.insert(0, first_digit)
            relevant_data = relevant_data[6*7*self.width:]
            # Get middle separator
            middle_separator = relevant_data[:5*self.width]
            if middle_separator != [255]*self.width + [0]*self.width + [255]*self.width + [0]*self.width + [255]*self.width:
                raise ValueError("Identification of middle separator failed")
            relevant_data = relevant_data[5*self.width:]

            # Get right 5 digits
            right_numbers = relevant_data[:5*7*self.width]
            reverse_right_even_parities = {v: k for k,
                                           v in self.right_even_parities.items()}
            for i in range(5):
                read_key = ""
                for j in range(7):
                    chunk = right_numbers[:self.width]
                    if chunk == [0]*self.width:
                        read_key += "1"
                    else:
                        read_key += "0"
                    right_numbers = right_numbers[self.width:]
                numbers_read.append(reverse_right_even_parities.get(read_key))
            relevant_data = relevant_data[5*7*self.width:]
            # Get the checksum
            checksum_digits = relevant_data[:7*self.width]
            checksum_digits = [
                1 if x == 0 else 0 for x in checksum_digits[::self.width]]
            numbers_read_ = []
            stored_checksum = reverse_right_even_parities.get(
                "".join(list(map(str, checksum_digits))))
            numbers_read_ = list(map(int, numbers_read))
            odd_sum = sum(map(lambda x: int(x)*3, numbers_read_[-1:1:-2]))
            even_sum = sum(map(lambda x: int(x), numbers_read_[-2:1:-2]))
            total_sum = odd_sum + even_sum
            mod_10 = total_sum % 10
            computed_checksum = (10 - mod_10) % 10
            if stored_checksum != str(computed_checksum):
                raise ValueError(
                    f"Identification of checksum failed. Stored={stored_checksum} Computed={computed_checksum}")
            relevant_data = relevant_data[7*self.width:]
            # Get right guard
            right_guard = relevant_data[:3*self.width]
            if right_guard != [0]*self.width + [255]*self.width + [0]*self.width:
                raise ValueError("Identification of right guard failed")
            relevant_data = relevant_data[3*self.width:]
            # Get the right quiet zone
            right_quiet_zone = relevant_data
            if right_quiet_zone != [255]*self.right_quiet_zone_width*self.width:
                raise ValueError("Identification of right quiet zone failed")
            if verbose:
                print(
                    f"Decoding complete. The barcode is {''.join(numbers_read)}-{computed_checksum}")

            return "".join(numbers_read)


if __name__ == "__main__":

    my_1_d_bar_obj = PoorMans1DBarCodeEncoderDecoder_EAN_13()
    my_1_d_bar_obj.encode("136000291452")
    # Verify the generated image by uploading in an online tool like below
    # https://orcascan.com/tools/gs1-barcode-decoder?barcode=0036000291452
    my_1_d_bar_obj.decode("Barcode_ean_13_136000291452-1.png", True)
