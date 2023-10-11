from datetime import timedelta, datetime
from numbers import Integral, Real
from pprint import pprint
import itertools
from collections import namedtuple
from enum import Enum
import unittest


class TimerError(Exception):
    """A custom exception used for Timer class"""


class TimeZone:

    def __init__(self, name, offset_hours, offset_minutes):

        if name is None or len(str(name).strip()) == 0:
            raise ValueError("TimeZone name cannot be empty.")

        self._name = str(name).strip()

        if not isinstance(offset_hours, Integral):
            raise ValueError("Hour offset must be an integer")
        
        if not isinstance(offset_minutes, Integral):
            raise ValueError("Minute offset must be an integer")

        if offset_minutes < -59 or offset_minutes > 59:
            raise ValueError("Minutes offset must be between -59 and 59 (inclusive).")

        offset = timedelta(hours=offset_hours, minutes=offset_minutes)
        if offset < timedelta(hours=-12, minutes=0) or offset > timedelta(hours=14, minutes=0):
            raise ValueError("Offset must be between -12:00 and +14:00.")

        self._offset_hours   = offset_hours
        self._offset_minutes = offset_minutes
        self._offset = offset

    
    @property
    def offset(self):
        return self._offset

    
    @property
    def name(self):
        return self._name

    
    def __eq__(self, other):
        return (
            isinstance(other, TimeZone) and 
            self.name == other.name and
            self._offset_hours == other._offset_hours and
            self._offset_minutes == other._offset_minutes
        )

    
    def __repr__(self):
        return (f"TimeZone(name='{self.name}', " 
                f"offset_hours={self._offset_hours}, "
                f"offset_minutes={self._offset_minutes})")




class TransactionID:

    def __init__(self, start_id):
        self._start_id = start_id
     
    def __next__(self):
        self._start_id += 1
        return self._start_id


Confirmation = namedtuple('Confirmation', 'account_number transaction_code transaction_id time_utc time')


class Transaction_Code(Enum):

    DEPOSIT  = 'D',
    WITHDRAW = 'W',
    INTEREST = 'I',
    REJECTED = 'X'


class Account():
    
    _interest_rate = 5 # Percent
    transaction_counter = itertools.count(100)


    def __init__(self, account_number, first_name, last_name, initial_balance=0, timezone=None):
        
        if not isinstance(account_number, Integral):
            raise ValueError("account_number must be an integer")

        if account_number < 0:
            raise ValueError("account_number cannot be negative numbers.")
        
        self._account_number = account_number
        self.first_name = first_name
        self.last_name  = last_name

        self._balance = Account.validate_real_number(initial_balance, 'balance', min_value=0.01)

        if timezone is None:
            timezone = TimeZone('UTC', 0, 0)
        self.timezone = timezone

    
    @property
    def balance(self):
        return self._balance
    

    def make_transaction_codes(self):
        new_trans_id = next(Account.transaction_counter)
        return new_trans_id


    @property
    def account_number(self):
        return self._account_number

    @property
    def first_name(self):
        return self._first_name


    @first_name.setter
    def first_name(self, value):
        self.validate_and_set_name('_first_name', value, 'first_name')


    @property
    def last_name(self):
        return self._last_name

    
    @last_name.setter
    def last_name(self, value):
        self.validate_and_set_name('_last_name', value, 'last_name')
    

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    
    @property
    def timezone(self):
        return self._timezone


    @timezone.setter
    def timezone(self, value):
        if not isinstance(value, TimeZone):
            raise ValueError('Time Zone must be a valid TimeZone object.')
        self._timezone = value


    @classmethod
    def get_interest_rate(cls):
        return cls._interest_rate


    @classmethod
    def set_interest_rate(cls, value):
        if not isinstance(value, Real):
            raise ValueError("interest rate must be real number.")

        if value < 0:
            raise ValueError("interest rate cannot be negative.")

        cls._interest_rate = value


    def validate_and_set_name(self, attr_name, value, field_title):
        if value is None or len(str(value).strip()) == 0:
            raise ValueError(f"{field_title} cannot be empty.")
        setattr(self, attr_name, value)

    
    @staticmethod    
    def validate_real_number(value, field_title, min_value=None):
        if not isinstance(value, Real):
            raise ValueError(f'{field_title} value must be a real number.')

        if min_value is not None and  value < min_value:
            raise ValueError(f'{field_title} value must at least {min_value}.')
        return value

    
    def generation_confirmation_code(self, transaction_code):
        dt_str = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        t_code = Transaction_Code[transaction_code].value[0]

        return (f"{t_code}-{self.account_number}-{dt_str}"
                f"-{next(Account.transaction_counter)}")


    @staticmethod
    def parse_confirmation_code(confirmation_code, preferred_time_zone=None):
        parts = confirmation_code.split('-')
        if len(parts) != 4:
            raise ValueError('Invalid confirmation code')
        transaction_code, account_number, raw_dt_utc, transaction_id = parts

        try:
            dt_utc = datetime.strptime(raw_dt_utc, '%Y%m%d%H%M%S')
        except ValueError as ex:
            raise ValueError('Invalid transaction datetime.') from ex
       
        if preferred_time_zone is None:
           preferred_time_zone = TimeZone('UTC', 0, 0)

        if not isinstance(preferred_time_zone, TimeZone):
            raise ValueError('Invalid TimeZone specified')
        
        dt_preferred = dt_utc + preferred_time_zone.offset
        dt_preferred_str = f"{dt_preferred.strftime('%Y%m%d%H%M%S')} ({preferred_time_zone.name})"
        
        return Confirmation(account_number, transaction_code,
                            transaction_id, dt_utc.isoformat(), dt_preferred_str)


    def deposit(self, value):
        value = Account.validate_real_number(value, 'deposit', 0.01)

        # Making a confirmation code
        conf_code = self.generation_confirmation_code('DEPOSIT')
        self._balance += value
        return conf_code

    
    def withdraw(self, value):
        value = Account.validate_real_number(value, 'withdraw', 0.01)

        accepted = False
        if value > self._balance:
            conf_code = self.generation_confirmation_code('REJECTED')
            return conf_code
        else:
            accepted = True
            conf_code = self.generation_confirmation_code('WITHDRAW')
       
        if accepted:
            self._balance -= value

        return conf_code
            
    
    def pay_interest(self):
        interest  = self.balance * Account.get_interest_rate() / 100
        conf_code = self.generation_confirmation_code('INTEREST')
        self._balance += interest
        return conf_code



def run_tests(test_class):
    suite  = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


class TestAccount(unittest.TestCase):

    def setUp(self):
        self.account_number = 400
        self.first_name = 'Mohammad'
        self.last_name  = 'Jalalnia'
        self.tz = TimeZone('IR', 3, 30)
        self.balance = 100.00

    
    def create_account(self):
        return Account(self.account_number, self.first_name, self.last_name, self.balance, self.tz)
    

    def test_create_timezone(self):
        tz = TimeZone('ABC', -1, -31)
        self.assertEqual('ABC', tz.name)
        self.assertEqual(timedelta(hours=-1, minutes=-31), tz.offset)


    def test_timezone_equal(self):
        tz1 = TimeZone('IR', 3, 30)
        tz2 = TimeZone('IR', 3, 30)
        self.assertEqual(tz1, tz2)


    def test_timezone_not_equal(self):
        tz = TimeZone('ABC', -1, -30)

        test_timezone = (
            TimeZone('IR', -1, -30),
            TimeZone('ABC', 1, -30),
            TimeZone('DEF', -1, -50),
        )

        for i, test_tz in enumerate(test_timezone):
            with self.subTest(test_name=f'Test # {i}'):
                self.assertNotEqual(tz, test_tz)


    def test_create_account(self):

        a = self.create_account()

        self.assertEqual(self.account_number, a.account_number)
        self.assertEqual(self.first_name, a.first_name)
        self.assertEqual(self.last_name, a.last_name)
        self.assertEqual(self.first_name + ' ' + self.last_name, a.full_name)
        self.assertEqual(self.tz, a.timezone)
        self.assertEqual(self.balance, a.balance)


    def test_create_account_blank_first_name(self):
        self.first_name = ''

        with self.assertRaises(ValueError):
            self.create_account()


    def test_create_account_negative_balance(self):
        self. balance = -100.00
        
        with self.assertRaises(ValueError):
            self.create_account()


    def test_account_withdraw_ok(self):
        withdraw_amout = 20

        a = self.create_account()
        conf_code = a.withdraw(withdraw_amout)

        self.assertTrue(conf_code.startswith('W-'))
        self.assertEqual(self.balance - withdraw_amout, a.balance)

    
    def test_account_withdraw_overdraft(self):
        withdraw_amout = 200

        a = self.create_account()
        conf_code = a.withdraw(withdraw_amout)

        self.assertTrue(conf_code.startswith('X-'))
        self.assertEqual(self.balance, a.balance)

run_tests(TestAccount)
