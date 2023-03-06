# credit to Fiore (https://github.com/donato-fiore)
import random


class Ctime:
    """
    A class to represent times in a comprehensible way.

    ...

    Attributes
    ----------
    seconds : int
        number of seconds to represent

    Methods
    -------
    get_random()
        returns the time in the comprehensible format
    """

    MAP = {
        4.76: "The ISS traveled {RESULT:,} mile{s}",
        18.5: "The Earth traveled {RESULT:,} mile{s}",
        4: "{RESULT:,} person{s} was born",
        2: "{RESULT:,} person{s} died",
        3391204: "{RESULT:,} email{s} was sent",
        250: "Bill Gates made ${RESULT:,.0f} USD",
        13324: "The US' national debt increased by ${RESULT:,.0f} USD",
        166: "{RESULT:,} rainforest tree{s} was cut down",
        30: "{RESULT:,} star{s} exploded",
        4800: "{RESULT:,} star{s} was created",
        52286: "{RESULT:,} person{s} donated to charity",
        9.2: "The universe expanded by {RESULT:,} mile{s}",
        1.74: "{RESULT:,.2f} ton{s} of food was thrown away",
        75: "{RESULT:,} McDonald's burger{s} was eaten",
        3000000: "{RESULT:,} Google search{s} was made",
        372: "{RESULT:,} person{s} searched for porn",
        25000: "{RESULT:,} person{s} had {AN}orgasm{s}",
    }

    def __init__(self, seconds: int):
        """
        Parameters
        ----------
        seconds : int
            number of seconds to represent
        """

        self.seconds = seconds

    def get_random(self) -> str:
        """
        returns the time in the comprehensible format.

        Returns
        -------
        str
        """

        multiplier = random.choice(list(self.MAP.keys()))
        unit = round(self.seconds * multiplier, 2)
        s = "s" if unit != 1 else ""
        an = "an " if unit == 1 else ""
        ret = (self.MAP[multiplier].replace("{s}", s).replace("{AN}", an)).format(RESULT=unit)
        if unit > 1:
            ret = ret.replace("persons", "people")
            ret = ret.replace("was", "were")

        if random.randint(0, 1):
            return f"{ret} in that time."
        return f"In that time, {ret[0].lower() + ret[1:]}."
