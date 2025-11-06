"""
Unit tests for swing_structure module.

Tests pivot detection, swing level calculation, and proximity signals.
Part of Item #7: Refactor/Integration Plan
"""

import pandas as pd
import numpy as np
import unittest
from datetime import datetime, timedelta
import swing_structure


class TestSwingStructure(unittest.TestCase):
    """Test cases for swing structure analysis functions."""
    
    def setUp(self):
        """Create sample price data for testing."""
        # Create a simple price pattern with clear pivots
        dates = pd.date_range(start='2024-01-01', periods=20, freq='D')
        
        # Price pattern: down, pivot low, up, pivot high, down
        prices_high = [105, 103, 101, 100, 102, 104, 106, 108, 107, 105, 
                       104, 103, 101, 99, 98, 97, 99, 101, 103, 105]
        prices_low = [103, 101, 99, 98, 100, 102, 104, 106, 105, 103, 
                      102, 101, 99, 97, 96, 95, 97, 99, 101, 103]
        prices_close = [104, 102, 100, 99, 101, 103, 105, 107, 106, 104, 
                        103, 102, 100, 98, 97, 96, 98, 100, 102, 104]
        
        self.df = pd.DataFrame({
            'High': prices_high,
            'Low': prices_low,
            'Close': prices_close,
            'Volume': [1000000] * 20
        }, index=dates)
    
    def test_find_pivots(self):
        """Test pivot detection with clear swing points."""
        pivot_lows, pivot_highs = swing_structure.find_pivots(self.df, lookback=3)
        
        # Check that we found some pivots
        self.assertTrue(pivot_lows.any(), "Should find at least one pivot low")
        self.assertTrue(pivot_highs.any(), "Should find at least one pivot high")
        
        # Check types
        self.assertIsInstance(pivot_lows, pd.Series)
        self.assertIsInstance(pivot_highs, pd.Series)
        
        # Check that pivot series are boolean
        self.assertTrue(pivot_lows.dtype == bool)
        self.assertTrue(pivot_highs.dtype == bool)
        
        # Check that pivot low occurs around index 3 (lowest point in pattern)
        # Note: Exact index depends on lookback confirmation
        pivot_low_indices = self.df.index[pivot_lows].tolist()
        self.assertGreater(len(pivot_low_indices), 0, "Should detect pivot low")
    
    def test_find_pivots_insufficient_data(self):
        """Test pivot detection with insufficient data."""
        # Create DataFrame with only 5 bars (need 7+ for lookback=3)
        small_df = self.df.head(5)
        
        pivot_lows, pivot_highs = swing_structure.find_pivots(small_df, lookback=3)
        
        # Should return all False (no pivots detected)
        self.assertFalse(pivot_lows.any())
        self.assertFalse(pivot_highs.any())
    
    def test_calculate_swing_levels(self):
        """Test swing level calculation."""
        swing_low, swing_high = swing_structure.calculate_swing_levels(self.df, lookback=3)
        
        # Check types and lengths
        self.assertIsInstance(swing_low, pd.Series)
        self.assertIsInstance(swing_high, pd.Series)
        self.assertEqual(len(swing_low), len(self.df))
        self.assertEqual(len(swing_high), len(self.df))
        
        # Check that levels are forward-filled (no NaN values)
        self.assertFalse(swing_low.isna().any(), "Swing low should be forward-filled")
        self.assertFalse(swing_high.isna().any(), "Swing high should be forward-filled")
        
        # Check that swing levels are reasonable (within price range)
        self.assertGreaterEqual(swing_low.min(), self.df['Low'].min())
        self.assertLessEqual(swing_high.max(), self.df['High'].max())
    
    def test_calculate_swing_proximity_signals_legacy(self):
        """Test swing proximity signals with legacy fixed percentage."""
        swing_low, swing_high = swing_structure.calculate_swing_levels(self.df, lookback=3)
        
        near_sup, lost_sup, near_res = swing_structure.calculate_swing_proximity_signals(
            self.df, swing_low, swing_high, 
            atr_series=None, 
            use_volatility_aware=False
        )
        
        # Check types
        self.assertIsInstance(near_sup, pd.Series)
        self.assertIsInstance(lost_sup, pd.Series)
        self.assertIsInstance(near_res, pd.Series)
        
        # Check boolean types
        self.assertTrue(near_sup.dtype == bool)
        self.assertTrue(lost_sup.dtype == bool)
        self.assertTrue(near_res.dtype == bool)
        
        # Check logical consistency: lost support should be a subset of not-near-support
        # (If lost support, then definitely not near support in normal cases)
        # Note: With 5% threshold for "near" and exact match for "lost", some overlap is expected
        both_triggered = near_sup & lost_sup
        # Allow reasonable overlap (up to 20% due to 5% proximity threshold)
        self.assertLess(both_triggered.sum(), len(self.df) * 0.2, 
                       "Near and lost support shouldn't overlap excessively")
    
    def test_calculate_swing_proximity_signals_volatility_aware(self):
        """Test swing proximity signals with ATR normalization."""
        # Add ATR column
        atr = pd.Series([2.0] * len(self.df), index=self.df.index)
        
        swing_low, swing_high = swing_structure.calculate_swing_levels(self.df, lookback=3)
        
        near_sup, lost_sup, near_res = swing_structure.calculate_swing_proximity_signals(
            self.df, swing_low, swing_high, 
            atr_series=atr, 
            use_volatility_aware=True
        )
        
        # Check that proximity scores were added to DataFrame
        self.assertIn('Support_Proximity', self.df.columns)
        self.assertIn('Resistance_Proximity', self.df.columns)
        
        # Check types
        self.assertTrue(near_sup.dtype == bool)
        self.assertTrue(lost_sup.dtype == bool)
        self.assertTrue(near_res.dtype == bool)
    
    def test_calculate_support_proximity_score(self):
        """Test support proximity score calculation."""
        swing_low, _ = swing_structure.calculate_swing_levels(self.df, lookback=3)
        atr = pd.Series([2.0] * len(self.df), index=self.df.index)
        
        prox_score = swing_structure.calculate_support_proximity_score(
            self.df, swing_low, atr
        )
        
        # Check type and length
        self.assertIsInstance(prox_score, pd.Series)
        self.assertEqual(len(prox_score), len(self.df))
        
        # Check that scores are numeric (not boolean)
        self.assertTrue(pd.api.types.is_numeric_dtype(prox_score))
    
    def test_identify_swing_failure_patterns(self):
        """Test swing failure pattern detection."""
        swing_low, swing_high = swing_structure.calculate_swing_levels(self.df, lookback=3)
        
        failed_bd, failed_bo = swing_structure.identify_swing_failure_patterns(
            self.df, swing_low, swing_high, lookback=5
        )
        
        # Check types
        self.assertIsInstance(failed_bd, pd.Series)
        self.assertIsInstance(failed_bo, pd.Series)
        self.assertTrue(failed_bd.dtype == bool)
        self.assertTrue(failed_bo.dtype == bool)
    
    def test_calculate_swing_strength(self):
        """Test swing strength calculation."""
        pivot_lows, pivot_highs = swing_structure.find_pivots(self.df, lookback=3)
        
        low_str, high_str = swing_structure.calculate_swing_strength(
            pivot_lows, pivot_highs, self.df, volume_threshold=1.5
        )
        
        # Check types and lengths
        self.assertIsInstance(low_str, pd.Series)
        self.assertIsInstance(high_str, pd.Series)
        self.assertEqual(len(low_str), len(self.df))
        self.assertEqual(len(high_str), len(self.df))
        
        # Check that strength scores are in 0-1 range (where they exist)
        # Note: Most bars will be 0 (not pivot points)
        valid_low_str = low_str[low_str > 0]
        valid_high_str = high_str[high_str > 0]
        
        if len(valid_low_str) > 0:
            self.assertTrue((valid_low_str >= 0).all())
            self.assertTrue((valid_low_str <= 1).all())
        
        if len(valid_high_str) > 0:
            self.assertTrue((valid_high_str >= 0).all())
            self.assertTrue((valid_high_str <= 1).all())


class TestSwingStructureIntegration(unittest.TestCase):
    """Integration tests for swing structure module."""
    
    def test_full_swing_workflow(self):
        """Test complete workflow from price data to proximity signals."""
        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        
        # Create V-shaped pattern (down then up) - should have clear pivot at bottom
        prices = []
        for i in range(15):
            prices.append(100 - i * 2)  # Down to 70
        for i in range(15):
            prices.append(70 + i * 2)  # Up to 98
        
        df = pd.DataFrame({
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Close': prices,
            'Volume': [1000000] * 30
        }, index=dates)
        
        # Calculate ATR for volatility-aware proximity
        df['TR'] = df['High'] - df['Low']
        df['ATR20'] = df['TR'].rolling(20).mean()
        
        # Run complete workflow
        # 1. Find pivots
        pivot_lows, pivot_highs = swing_structure.find_pivots(df, lookback=3)
        
        # Should find pivot at bottom of V
        self.assertTrue(pivot_lows.any(), "Should find pivot low at V bottom")
        
        # 2. Calculate swing levels
        swing_low, swing_high = swing_structure.calculate_swing_levels(df, lookback=3)
        
        # Swing low should update after pivot is confirmed
        self.assertFalse(swing_low.isna().any())
        
        # 3. Calculate proximity signals
        near_sup, lost_sup, near_res = swing_structure.calculate_swing_proximity_signals(
            df, swing_low, swing_high,
            atr_series=df['ATR20'],
            use_volatility_aware=True
        )
        
        # Check that proximity signals exist (some may be all False, that's ok)
        self.assertIsInstance(near_sup, pd.Series)
        self.assertIsInstance(lost_sup, pd.Series)
        self.assertIsInstance(near_res, pd.Series)
        
        # 4. After pivot low is confirmed and price rises, we should have:
        #    - swing_low stable at the V bottom
        #    - near_support triggered when close to that level
        #    - lost_support NOT triggered (since we bounced up)
        
        # Price should rise after pivot - check last 5 bars are above swing low
        last_5_above_support = (df['Close'].tail(5) > swing_low.tail(5)).all()
        self.assertTrue(last_5_above_support, "Price should be above support after V bounce")


if __name__ == '__main__':
    print("Running swing_structure module tests...")
    unittest.main(verbosity=2)
