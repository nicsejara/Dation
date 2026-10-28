from datetime import date
from decimal import Decimal, localcontext
import unittest

from app.domain.logistics.transit import TransitEstimator


class UltimateTransitTests(unittest.TestCase):
    def test_standard_distance_boundaries(self):
        for distance, expected in [(120,1),(500,1),(501,2),(1000,2),(1001,3)]:
            with self.subTest(distance=distance):
                self.assertEqual(TransitEstimator.estimate(distance,'EXTERNAL').outbound_days,expected)

    def test_own_cycle_is_independent_from_twice_rounded_outbound(self):
        result=TransitEstimator.estimate(480,'OWN')
        self.assertEqual((result.outbound_days,result.cycle_days),(1,2))
        self.assertEqual(TransitEstimator.estimate(501,'OWN').cycle_days,3)
        self.assertEqual(TransitEstimator.estimate(1000,'OWN').cycle_days,4)

    def test_external_has_no_return_occupancy(self):
        result=TransitEstimator.estimate(480,'EXTERNAL')
        self.assertIsNone(result.cycle_days)
        dates=TransitEstimator.dates(date(2026,11,2),480,'EXTERNAL')
        self.assertEqual(dates.arrival,date(2026,11,2))
        self.assertIsNone(dates.available_again)

    def test_inclusive_arrival_and_exclusive_own_availability(self):
        result=TransitEstimator.dates(date(2026,11,2),480,'OWN')
        self.assertEqual(result.arrival,date(2026,11,2))
        self.assertEqual(result.available_again,date(2026,11,4))
        result=TransitEstimator.dates(date(2026,11,2),1150,'OWN')
        self.assertEqual(result.arrival,date(2026,11,4))
        self.assertEqual(result.available_again,date(2026,11,7))

    def test_calendar_crosses_month_and_leap_day(self):
        result=TransitEstimator.dates(date(2028,2,28),501,'OWN')
        self.assertEqual(result.arrival,date(2028,2,29))
        self.assertEqual(result.available_again,date(2028,3,2))

    def test_horizon_limits_departures_not_arrivals(self):
        result=TransitEstimator.dates(date(2026,11,8),1000,'OWN')
        self.assertEqual(result.arrival,date(2026,11,9))
        self.assertEqual(result.available_again,date(2026,11,12))

    def test_exact_decimal_boundary_and_context_independence(self):
        for precision in (2,28,60):
            with localcontext() as ctx:
                ctx.prec=precision
                self.assertEqual(TransitEstimator.estimate(Decimal('500.001'),'OWN').outbound_days,2)
                self.assertEqual(TransitEstimator.estimate('480','OWN').cycle_days,2)

    def test_invalid_distance_source_and_timestamp_fail_closed(self):
        for invalid in (0,-1,True,500.0,'NaN','Infinity','bad'):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                TransitEstimator.estimate(invalid,'OWN')
        with self.assertRaises(ValueError):TransitEstimator.estimate(500,'unknown')
        with self.assertRaises(ValueError):TransitEstimator.dates('2026-11-02',500,'OWN')


if __name__=='__main__':unittest.main()
