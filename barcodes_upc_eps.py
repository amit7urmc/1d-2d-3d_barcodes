"""
This module implements various 1D barcode encoders and decoders.
"""
import turtle
import re


class PoorMans1DBarCodeEncoderDecoder_UPC_A:
    """
    This class implements the UPC-A class of 1D barcode encoding and decoding via eps image.
    """

    def __init__(self,
                 width=3,  # Keep it an odd number
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
        self.screen = turtle.Screen()
        self.screen.screensize(200*self.width, self.height+20)
        self.screen.setup(1.0, 1.0)

        self.turtle_pen = turtle.Turtle()
        self.turtle_pen.hideturtle()
        self.turtle_pen.speed(0)

        self.eps_pattern_of_interest = re.compile(
            r"^(?P<X>\d+)\s(?P<Y>\d+)\slineto$")

    def encode(self, number_to_encode: str):
        """
        Given a number in a string form, this method creates an eps image having the bar codes.
        """
        # Encode the 101 ..left boundary
        self.turtle_pen.width(self.width)
        pos = 0
        for i in "101":
            if int(i):
                x_pos = (pos)*self.width+self.width//2
                self.turtle_pen.setpos(x_pos, 0)
                self.turtle_pen.pendown()
                self.turtle_pen.goto(x_pos, self.height)
                self.turtle_pen.penup()
            pos += 1
        # Encode left 6 digits
        for i in number_to_encode[:6:]:
            for number in self.left_odd_parities[i]:
                if int(number):
                    x_pos = (pos)*self.width+self.width//2
                    self.turtle_pen.setpos(x_pos, 0)
                    self.turtle_pen.pendown()
                    self.turtle_pen.goto(x_pos, self.height)
                    self.turtle_pen.penup()
                pos += 1
        # Encode 01010 .. Central separator
        for i in "01010":
            if int(i):
                x_pos = (pos)*self.width+self.width//2
                self.turtle_pen.setpos(x_pos, 0)
                self.turtle_pen.pendown()
                self.turtle_pen.goto(x_pos, self.height)
                self.turtle_pen.penup()
            pos += 1
        # Encode right 5 digits
        for i in number_to_encode[6:-1:]:
            for number in self.right_even_parities[i]:
                if int(number):
                    x_pos = (pos)*self.width+self.width//2
                    self.turtle_pen.setpos(x_pos, 0)
                    self.turtle_pen.pendown()
                    self.turtle_pen.goto(x_pos, self.height)
                    self.turtle_pen.penup()
                pos += 1
        # Encode the checksum
        odd_sum = sum(map(lambda x: int(x)*3, number_to_encode[::2]))
        even_sum = sum(map(lambda x: int(x), number_to_encode[1:-1:2]))
        total_sum = odd_sum + even_sum
        mod_10 = total_sum % 10
        inverse_mod_10 = (10 - mod_10) % 10
        encoded_checksum = self.right_even_parities[str(inverse_mod_10)]
        for number in encoded_checksum:
            if int(number):
                x_pos = (pos)*self.width+self.width//2
                self.turtle_pen.setpos(x_pos, 0)
                self.turtle_pen.pendown()
                self.turtle_pen.goto(x_pos, self.height)
                self.turtle_pen.penup()
            pos += 1
        # Encode the 101 .. right boundary
        for i in "101":
            if int(i):
                x_pos = (pos)*self.width+self.width//2
                self.turtle_pen.setpos(x_pos, 0)
                self.turtle_pen.pendown()
                self.turtle_pen.goto(x_pos, self.height)
                self.turtle_pen.penup()
            pos += 1
        canvas = self.screen.getcanvas()
        canvas.postscript(file=f"Barcode_{number_to_encode}.eps")
        print("We encoded the number in a postscript file as a 1D barcode. Please close the popup to continue")
        self.screen.exitonclick()

    def extract_binary(self, eps_image_to_read, verbose=False):
        """
        This image extracts a binary string from the saved eps image.
        """
        bar_code = ""
        width = None
        height = None
        # Scan for left 101
        height_width_processed = False
        with open(eps_image_to_read, "r") as filehandle:
            line_holder = []
            last_known_x, current_x = None, None
            while (current_line := filehandle.readline().strip()) != "%%EOF":
                if current_line.endswith("lineto") and len(line_holder) < 3:
                    # Add and process
                    line_holder.append(current_line)
                if len(line_holder) == 3 and not height_width_processed:
                    X1, Y1 = self.eps_pattern_of_interest.match(
                        line_holder[0]).groups()
                    X1_, Y2 = self.eps_pattern_of_interest.match(
                        line_holder[1]).groups()
                    X2, Y1_ = self.eps_pattern_of_interest.match(
                        line_holder[2]).groups()
                    assert X1 == X1_
                    width = (int(X2)-int(X1))//2
                    height = int(Y2) - int(Y1)
                    height_width_processed = True
                    last_known_x, current_x = X2, X2
                    bar_code += "101"
                    continue
                if width and height:
                    current_x = self.eps_pattern_of_interest.match(
                        current_line)
                    if current_x:
                        gap = int(current_x.group("X")) - int(last_known_x)
                        if gap == width:
                            bar_code += "1"
                        else:
                            num_zeros = gap//width - 1
                            bar_code += "0"*num_zeros + "1"
                        last_known_x = int(current_x.group("X"))
        if verbose:
            print(f"The decoded binary string for the eps image is {bar_code}")
        assert len(
            bar_code) == 95, f"{len(bar_code)} We missed at least one bar/gap.   ...---... "
        return bar_code

    def decode(self, eps_image_to_read, verbose):
        """
        This method decodes the eps image into the number
        """
        binary_bar_code = self.extract_binary(
            eps_image_to_read=eps_image_to_read, verbose=verbose)
        left_numbers = binary_bar_code[3:3+(6*7)]
        right_numbers = binary_bar_code[3+(6*7)+5:-3]
        assert len(left_numbers) == 42
        assert len(right_numbers) == 42
        decoded_number = ""
        revsered_left_parities = {v: k for k,
                                  v in self.left_odd_parities.items()}
        for left_slice_index in range(0, 42, 7):
            left_slice = left_numbers[left_slice_index:left_slice_index+7]
            decoded_number += revsered_left_parities[left_slice]
        revsered_right_parities = {v: k for k,
                                   v in self.right_even_parities.items()}
        for right_slice_index in range(0, 42, 7):
            right_slice = right_numbers[right_slice_index:right_slice_index+7]
            decoded_number += revsered_right_parities[right_slice]
        # Assert the checksum
        odd_sum = sum(map(lambda x: int(x)*3, decoded_number[::2]))
        even_sum = sum(map(lambda x: int(x), decoded_number[1:-1:2]))
        total_sum = odd_sum + even_sum
        mod_10 = total_sum % 10
        inverse_mod_10 = (10 - mod_10) % 10
        encoded_checksum = inverse_mod_10
        assert str(encoded_checksum) == decoded_number[
            -1], f"The checksum failed. {(encoded_checksum)} != {decoded_number[-1]}  The image is corrupted/invalid."
        if verbose:
            print(f"The decoded number from the .eps file is {decoded_number}")
        return decoded_number


class PoorMans1DBarCodeEncoderDecoder_EAN_13(PoorMans1DBarCodeEncoderDecoder_UPC_A):
    """
    This class implements EAN-13 standard 1D bar codes.
    """
    pass


if __name__ == "__main__":

    my_1_d_bar_obj = PoorMans1DBarCodeEncoderDecoder_UPC_A()
    my_1_d_bar_obj.encode("036000291452")
    my_1_d_bar_obj.decode("Barcode_036000291452.eps", True)
