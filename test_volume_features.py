"""
Unit tests for volume_features module.

Tests CMF calculation, volume analysis, and event detection.
Part of Item #7: Refactor/Integration Plan
"""

import pandas as pd
import numpy as np
import unittest
from datetime import datetime, timedelta
import volume_features


class TestVolumeFeatures(unittest.TestCase):
    """Test cases for volume analysis functions."""
    
    def setUp(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        
        # Create varied price and volume data
        self.df = pd.DataFrame({
            'Open': [100 + i * 0.5 for i in range(30)],
            'High': [102 + i * 0.5 for i in range(30)],
            'Low': [99 + i * 0.5 for i in range(30)],
            'Close': [101 + i * 0.5 for i in range(30)],
            'Volume': [1000000 + i * 50000 for i in range(30)]
        }, index=dates)
    
    def test_calculate_cmf(self):
        """Test Chaikin Money Flow calculation."""
        cmf = volume_features.calculate_cmf(self.df, period=20)
        
        # Check type and length
        self.assertIsInstance(cmf, pd.Series)
        self.assertEqual(len(cmf), len(self.df))
        
        # CMF should be in range -1 to +1
        valid_cmf = cmf.dropna()
        self.assertTrue((valid_cmf >= -1).all(), "CMF should be >= -1")
        self.assertTrue((valid_cmf <= 1).all(), "CMF should be <= +1")
        
        # Check that CMF has some non-zero values (not all neutral)
        self.assertTrue((valid_cmf != 0).any(), "CMF should have non-zero values")
    
    def test_calculate_cmf_edge_cases(self):
        """Test CMF with edge cases (zero range, missing data)."""
        # Create DataFrame with zero-range bars (High == Low)
        df_zero_range = self.df.copy()
        df_zero_range.loc[df_zero_range.index[5], 'High'] = df_zero_range.loc[df_zero_range.index[5], 'Low']
        
        cmf = volume_features.calculate_cmf(df_zero_range, period=20)
        
        # Should handle zero range gracefully (no errors, no inf values)
        self.assertFalse(np.isinf(cmf).any(), "CMF should not contain inf values")
        # CMF rolling calculation needs warmup period, allow some NaN values
        valid_cmf = cmf.dropna()
        self.assertGreater(len(valid_cmf), 0, "Should have some valid CMF values")
    
    def test_calculate_cmf_zscore(self):
        """Test CMF z-score normalization."""
        # Need enough data for double windowing (20 CMF + 20 z-score = 40 minimum)
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        df_long = pd.DataFrame({
            'Open': [100 + i * 0.5 for i in range(50)],
            'High': [102 + i * 0.5 for i in range(50)],
            'Low': [99 + i * 0.5 for i in range(50)],
            'Close': [101 + i * 0.5 for i in range(50)],
            'Volume': [1000000 + i * 50000 for i in range(50)]
        }, index=dates)
        
        cmf_z = volume_features.calculate_cmf_zscore(df_long, cmf_period=20, zscore_window=20)
        
        # Check type and length
        self.assertIsInstance(cmf_z, pd.Series)
        self.assertEqual(len(cmf_z), len(df_long))
        
        # Z-scores typically range from -3 to +3 (but can exceed)
        valid_z = cmf_z.dropna()
        self.assertTrue(len(valid_z) > 0, "Should have some valid z-scores")
        
        # Check that z-scores are numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(cmf_z))
    
    def test_calculate_volume_surprise(self):
        """Test volume surprise (relative volume) calculation."""
        vol_surprise = volume_features.calculate_volume_surprise(self.df, window=20)
        
        # Check type and length
        self.assertIsInstance(vol_surprise, pd.Series)
        self.assertEqual(len(vol_surprise), len(self.df))
        
        # Volume surprise should be positive (ratio)
        valid_surprise = vol_surprise.dropna()
        self.assertTrue((valid_surprise > 0).all(), "Volume surprise should be positive")
        
        # With increasing volume in our test data, later values should be >1.0
        self.assertTrue((vol_surprise.tail(10) > 1.0).any(), "Should detect volume increase")
    
    def test_detect_event_days(self):
        """Test event day detection (ATR and volume spikes)."""
        # Add required columns for event detection
        self.df['TR'] = self.df['High'] - self.df['Low']
        self.df['ATR20'] = self.df['TR'].rolling(20).mean()
        self.df['Relative_Volume'] = volume_features.calculate_volume_surprise(self.df, window=20)
        
        # Create an artificial event day (high TR and high volume)
        event_idx = self.df.index[25]
        self.df.loc[event_idx, 'TR'] = self.df['ATR20'].iloc[25] * 3.0  # 3x ATR spike
        self.df.loc[event_idx, 'Volume'] = self.df['Volume'].iloc[25] * 2.5  # 2.5x volume
        self.df['Relative_Volume'] = self.df['Volume'] / self.df['Volume'].rolling(20).mean()
        
        # Detect event days
        event_days = volume_features.detect_event_days(
            self.df, 
            atr_multiplier=2.5, 
            volume_threshold=2.0
        )
        
        # Check type
        self.assertIsInstance(event_days, pd.Series)
        self.assertTrue(event_days.dtype == bool)
        
        # Should detect the artificial event day
        self.assertTrue(event_days.loc[event_idx], "Should detect artificial event day")
        
        # Most other days should NOT be event days
        self.assertLess(event_days.sum(), len(self.df) * 0.2, "Event days should be rare")
    
    def test_calculate_volume_trend(self):
        """Test volume trend calculation."""
        vol_trend = volume_features.calculate_volume_trend(
            self.df, short_window=5, long_window=20
        )
        
        # Check type and length
        self.assertIsInstance(vol_trend, pd.Series)
        self.assertEqual(len(vol_trend), len(self.df))
        
        # Volume trend should be in -1 to +1 range
        valid_trend = vol_trend.dropna()
        self.assertTrue((valid_trend >= -1).all(), "Volume trend should be >= -1")
        self.assertTrue((valid_trend <= 1).all(), "Volume trend should be <= +1")
        
        # With increasing volume, trend should be positive
        self.assertTrue((vol_trend.tail(10) > 0).any(), "Should detect volume uptrend")
    
    def test_detect_volume_divergence(self):
        """Test volume-price divergence detection."""
        # Add CMF column required for divergence
        self.df['CMF_20'] = volume_features.calculate_cmf(self.df, period=20)
        
        bull_div, bear_div = volume_features.detect_volume_divergence(
            self.df, price_window=10, volume_window=10
        )
        
        # Check types
        self.assertIsInstance(bull_div, pd.Series)
        self.assertIsInstance(bear_div, pd.Series)
        self.assertTrue(bull_div.dtype == bool)
        self.assertTrue(bear_div.dtype == bool)
        
        # Check logical consistency: can't have both divergences simultaneously
        both = bull_div & bear_div
        self.assertFalse(both.any(), "Can't have bullish AND bearish divergence simultaneously")
    
    def test_detect_climax_volume(self):
        """Test climax volume detection."""
        # Add relative volume
        self.df['Relative_Volume'] = volume_features.calculate_volume_surprise(self.df, window=20)
        
        # Create artificial climax (high volume + big move)
        climax_idx = self.df.index[25]
        self.df.loc[climax_idx, 'Volume'] = self.df['Volume'].iloc[24] * 4.0
        self.df.loc[climax_idx, 'Close'] = self.df['Close'].iloc[24] * 1.03  # +3% move
        self.df['Relative_Volume'] = self.df['Volume'] / self.df['Volume'].rolling(20).mean()
        
        buy_climax, sell_climax = volume_features.detect_climax_volume(
            self.df, volume_threshold=3.0, price_threshold=0.02
        )
        
        # Check types
        self.assertIsInstance(buy_climax, pd.Series)
        self.assertIsInstance(sell_climax, pd.Series)
        self.assertTrue(buy_climax.dtype == bool)
        self.assertTrue(sell_climax.dtype == bool)
        
        # Should detect the artificial buying climax
        self.assertTrue(buy_climax.loc[climax_idx], "Should detect buying climax")
    
    def test_calculate_volume_efficiency(self):
        """Test volume efficiency calculation."""
        vol_eff = volume_features.calculate_volume_efficiency(self.df, period=20)
        
        # Check type and length
        self.assertIsInstance(vol_eff, pd.Series)
        self.assertEqual(len(vol_eff), len(self.df))
        
        # Efficiency should be positive
        valid_eff = vol_eff.dropna()
        self.assertTrue((valid_eff > 0).all(), "Volume efficiency should be positive")
    
    def test_calculate_volume_weighted_momentum(self):
        """Test volume-weighted momentum calculation."""
        vw_mom = volume_features.calculate_volume_weighted_momentum(self.df, period=10)
        
        # Check type and length
        self.assertIsInstance(vw_mom, pd.Series)
        self.assertEqual(len(vw_mom), len(self.df))
        
        # With rising prices and increasing volume, should see positive momentum
        valid_mom = vw_mom.dropna()
        self.assertTrue((valid_mom > 0).any(), "Should detect positive momentum")
    
    def test_calculate_volume_profile(self):
        """Test volume profile calculation."""
        profile = volume_features.calculate_volume_profile(
            self.df, price_bins=20, lookback=30
        )
        
        # Check type
        self.assertIsInstance(profile, pd.DataFrame)
        
        # Check columns
        self.assertIn('price_level', profile.columns)
        self.assertIn('volume', profile.columns)
        self.assertIn('volume_pct', profile.columns)
        
        # Check that volume percentages sum to ~100%
        total_pct = profile['volume_pct'].sum()
        self.assertAlmostEqual(total_pct, 100.0, delta=0.1, 
                              msg="Volume percentages should sum to 100%")
        
        # Check that price levels are within data range
        self.assertGreaterEqual(profile['price_level'].min(), self.df['Close'].min())
        self.assertLessEqual(profile['price_level'].max(), self.df['Close'].max())


class TestVolumeFeaturesDivergence(unittest.TestCase):
    """Specialized tests for volume divergence detection."""
    
    def test_bullish_divergence_pattern(self):
        """Test detection of bullish divergence (price down, CMF up)."""
        # Create specific divergence pattern
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        
        # Price declining for first 15 days, then stabilizing
        prices = [100 - i * 0.5 for i in range(15)] + [92.5] * 35
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Close': prices,
            'Volume': [1000000 + i * 100000 for i in range(50)]  # Increasing volume
        }, index=dates)
        
        # Calculate CMF
        df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
        
        # Detect divergence
        bull_div, bear_div = volume_features.detect_volume_divergence(
            df, price_window=10, volume_window=10
        )
        
        # Check that function runs and returns correct types
        self.assertIsInstance(bull_div, pd.Series)
        self.assertIsInstance(bear_div, pd.Series)
        self.assertTrue(bull_div.dtype == bool)
        self.assertTrue(bear_div.dtype == bool)
    
    def test_bearish_divergence_pattern(self):
        """Test detection of bearish divergence (price up, CMF down)."""
        # Create specific divergence pattern
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        
        # Price rising but volume declining (distribution pattern)
        prices = [100 + i * 0.5 for i in range(50)]
        volumes = [2000000 - i * 30000 for i in range(50)]  # Decreasing volume
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Close': prices,
            'Volume': volumes
        }, index=dates)
        
        # Calculate CMF
        df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
        
        # Detect divergence
        bull_div, bear_div = volume_features.detect_volume_divergence(
            df, price_window=10, volume_window=10
        )
        
        # Check that function runs and returns correct types
        self.assertIsInstance(bull_div, pd.Series)
        self.assertIsInstance(bear_div, pd.Series)
        self.assertTrue(bull_div.dtype == bool)
        self.assertTrue(bear_div.dtype == bool)


class TestVolumeFeaturesCMF(unittest.TestCase):
    """Specialized tests for CMF calculation (Item #10)."""
    
    def setUp(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        
        # Create varied price and volume data
        self.df = pd.DataFrame({
            'Open': [100 + i * 0.5 for i in range(30)],
            'High': [102 + i * 0.5 for i in range(30)],
            'Low': [99 + i * 0.5 for i in range(30)],
            'Close': [101 + i * 0.5 for i in range(30)],
            'Volume': [1000000 + i * 50000 for i in range(30)]
        }, index=dates)
    
    def test_cmf_buying_pressure(self):
        """Test CMF detects buying pressure (closes near highs)."""
        dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
        
        # Create pattern with closes near highs (buying pressure)
        df = pd.DataFrame({
            'Open': [100] * 25,
            'High': [105] * 25,
            'Low': [95] * 25,
            'Close': [104] * 25,  # Close near high
            'Volume': [1000000] * 25
        }, index=dates)
        
        cmf = volume_features.calculate_cmf(df, period=20)
        
        # CMF should be positive (buying pressure)
        valid_cmf = cmf.dropna()
        self.assertTrue((valid_cmf > 0).all(), "CMF should be positive for closes near highs")
    
    def test_cmf_selling_pressure(self):
        """Test CMF detects selling pressure (closes near lows)."""
        dates = pd.date_range(start='2024-01-01', periods=25, freq='D')
        
        # Create pattern with closes near lows (selling pressure)
        df = pd.DataFrame({
            'Open': [100] * 25,
            'High': [105] * 25,
            'Low': [95] * 25,
            'Close': [96] * 25,  # Close near low
            'Volume': [1000000] * 25
        }, index=dates)
        
        cmf = volume_features.calculate_cmf(df, period=20)
        
        # CMF should be negative (selling pressure)
        valid_cmf = cmf.dropna()
        self.assertTrue((valid_cmf < 0).all(), "CMF should be negative for closes near lows")
    
    def test_cmf_zscore_normalization(self):
        """Test that CMF z-score provides normalized values."""
        cmf_z = volume_features.calculate_cmf_zscore(self.df, cmf_period=20, zscore_window=20)
        
        # Z-scores should have mean near 0 and std near 1 (after warm-up period)
        valid_z = cmf_z.dropna()
        
        if len(valid_z) > 0:
            # Mean should be close to 0
            self.assertLess(abs(valid_z.mean()), 0.5, "Z-score mean should be near 0")
            
            # Std should be close to 1
            if len(valid_z) >= 20:
                std_dev = valid_z.std()
                self.assertGreater(std_dev, 0.5, "Z-score std should be reasonable")
                self.assertLess(std_dev, 2.0, "Z-score std should be reasonable")


class TestVolumeEventDetection(unittest.TestCase):
    """Specialized tests for event day detection (Item #3)."""
    
    def test_detect_event_days_spike(self):
        """Test event detection with ATR and volume spikes."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        
        # Create normal data
        df = pd.DataFrame({
            'Open': [100] * 30,
            'High': [102] * 30,
            'Low': [98] * 30,
            'Close': [100] * 30,
            'Volume': [1000000] * 30
        }, index=dates)
        
        # Calculate ATR
        df['TR'] = df['High'] - df['Low']
        df['ATR20'] = df['TR'].rolling(20).mean()
        df['Relative_Volume'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        # Create event day at index 25
        event_idx = df.index[25]
        df.loc[event_idx, 'High'] = 112  # Big range
        df.loc[event_idx, 'Low'] = 88
        df.loc[event_idx, 'TR'] = 24  # 24 vs normal 4 = 6x spike
        df.loc[event_idx, 'Volume'] = 3000000  # 3x normal
        
        # Recalculate relative volume
        df['Relative_Volume'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        # Detect event days
        event_days = volume_features.detect_event_days(
            df, atr_multiplier=2.5, volume_threshold=2.0
        )
        
        # Should detect the spike day
        self.assertTrue(event_days.loc[event_idx], "Should detect event day")
        
        # Should NOT detect normal days
        normal_days = event_days.drop(event_idx)
        self.assertFalse(normal_days.any(), "Normal days should not be event days")
    
    def test_detect_event_days_requires_both(self):
        """Test that event detection requires BOTH ATR spike AND volume spike."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        
        df = pd.DataFrame({
            'Open': [100] * 30,
            'High': [102] * 30,
            'Low': [98] * 30,
            'Close': [100] * 30,
            'Volume': [1000000] * 30
        }, index=dates)
        
        df['TR'] = df['High'] - df['Low']
        df['ATR20'] = df['TR'].rolling(20).mean()
        df['Relative_Volume'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        # Create day with ONLY ATR spike (no volume spike)
        atr_only_idx = df.index[20]
        df.loc[atr_only_idx, 'TR'] = df['ATR20'].iloc[20] * 3.0
        
        # Create day with ONLY volume spike (no ATR spike)
        vol_only_idx = df.index[22]
        df.loc[vol_only_idx, 'Volume'] = 3000000
        
        # Recalculate relative volume
        df['Relative_Volume'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        # Detect event days
        event_days = volume_features.detect_event_days(
            df, atr_multiplier=2.5, volume_threshold=2.0
        )
        
        # Should NOT detect days with only one condition
        self.assertFalse(event_days.loc[atr_only_idx], "ATR spike alone is not event day")
        self.assertFalse(event_days.loc[vol_only_idx], "Volume spike alone is not event day")


class TestVolumeIntegration(unittest.TestCase):
    """Integration tests for volume module."""
    
    def test_complete_volume_analysis_workflow(self):
        """Test complete volume analysis from OHLCV to signals."""
        # Create realistic multi-week data
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        
        # Create trending data with volume patterns
        base_price = 100
        prices = []
        volumes = []
        
        for i in range(60):
            # Uptrend with pullbacks
            trend = i * 0.3
            noise = np.sin(i * 0.3) * 2
            price = base_price + trend + noise
            prices.append(price)
            
            # Volume increases on trend days
            volume = 1000000 * (1 + abs(np.sin(i * 0.3)))
            volumes.append(volume)
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p + 2 for p in prices],
            'Low': [p - 2 for p in prices],
            'Close': prices,
            'Volume': volumes
        }, index=dates)
        
        # Run complete analysis
        # 1. CMF
        df['CMF_20'] = volume_features.calculate_cmf(df, period=20)
        df['CMF_Z'] = volume_features.calculate_cmf_zscore(df, cmf_period=20, zscore_window=20)
        
        # 2. Volume metrics
        df['Relative_Volume'] = volume_features.calculate_volume_surprise(df, window=20)
        df['Volume_Trend'] = volume_features.calculate_volume_trend(df, short_window=5, long_window=20)
        
        # 3. ATR and event detection
        df['TR'] = df['High'] - df['Low']
        df['ATR20'] = df['TR'].rolling(20).mean()
        df['Event_Day'] = volume_features.detect_event_days(df, atr_multiplier=2.5, volume_threshold=2.0)
        
        # 4. Divergence
        bull_div, bear_div = volume_features.detect_volume_divergence(df)
        df['Bullish_Div'] = bull_div
        df['Bearish_Div'] = bear_div
        
        # Verify all metrics were calculated
        self.assertIn('CMF_20', df.columns)
        self.assertIn('CMF_Z', df.columns)
        self.assertIn('Relative_Volume', df.columns)
        self.assertIn('Volume_Trend', df.columns)
        self.assertIn('Event_Day', df.columns)
        self.assertIn('Bullish_Div', df.columns)
        
        # Check that we have valid data (not all NaN)
        self.assertTrue(df['CMF_20'].notna().any())
        self.assertTrue(df['Relative_Volume'].notna().any())
        
        # Check data quality (no inf values)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            self.assertFalse(np.isinf(df[col]).any(), f"{col} should not contain inf values")


if __name__ == '__main__':
    print("Running volume_features module tests...")
    unittest.main(verbosity=2)
