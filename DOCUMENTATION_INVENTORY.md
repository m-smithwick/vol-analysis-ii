# Documentation Inventory

**Last Updated:** December 10, 2025  
**Purpose:** Comprehensive inventory of all documentation in the vol-analysis-ii trading system  
**Status:** Pre-consolidation inventory (master index will be created after reorganization)

---

## 📊 INVENTORY SUMMARY

- **Total Documentation Files:** 70+
- **Total Directories with Docs:** 4 (root, docs/, configs/, upgrade-docs/)
- **Categories:** 12
- **Primary Languages:** Markdown (.md), YAML (.yaml), Text (.txt)

---

## 1️⃣ CORE STRATEGIC DOCUMENTATION

### Primary Trading Strategy
| File | Location | Size | Purpose | Status |
|------|----------|------|---------|--------|
| `TRADING_STRATEGY.md` | Root | 89KB | Main trading strategy guide with volume analysis methodology, signal types, risk management, and execution strategies | ✅ Current (Updated Dec 10, 2025 - added Position Sizing Mechanics section) |
| `SECTOR_ROTATION_ANALYSIS_GUIDE.md` | Root | - | Sector rotation analysis tools and proposed adaptive strategy (NOT IMPLEMENTED in code) | ✅ Updated Dec 10, 2025 - Added status banner clarifying tools exist but adaptive logic not implemented |

**Status:** ✅ RESOLVED - File renamed from TRADING_STRATEGY_SECTOR_AWARE.md with clear status warnings added.

---

## 2️⃣ ARCHITECTURE & CODE REFERENCE

### System Architecture
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `CODE_MAP.txt` | Root | Module responsibilities, dependencies, and routing map for quick lookup | ✅ Current (Updated Dec 10, 2025 - Added cross-references to ARCHITECTURE_REFERENCE and DOCUMENTATION_INVENTORY, added sector tools clarification) |
| `ARCHITECTURE_REFERENCE.md` | docs/ | Conceptual architecture overview complementing CODE_MAP | ✅ Current (Updated Dec 10, 2025 - Added cross-references to CODE_MAP and DOCUMENTATION_INVENTORY) |
| `ALGORITHM_IMPROVEMENT_PLAN.md` | Root | 5-phase roadmap for position sizing and drawdown protection | ✅ Active roadmap |

**Status:** ✅ RESOLVED - Cross-references added between CODE_MAP and ARCHITECTURE_REFERENCE for better LLM navigation.

---

## 3️⃣ OPERATIONS MANUALS

### Daily Operations & Workflows
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `USER_PLAYBOOK.md` | docs/ | Daily operations guide for traders | ✅ Current |
| `EOD_DATA_WORKFLOW.md` | docs/ | End-of-day data workflow and procedures | ✅ Current |
| `BULK_CACHE_POPULATION.md` | docs/ | Cache population and management procedures | ✅ Current |
| `git-workflow.md` | Root | Version control workflow | ✅ Current |
| `session-close.md` | Root | Session management procedures | ✅ Current |

**Recommendation:** Consolidate into single Operations Manual with chapters.

---

## 4️⃣ TECHNICAL SPECIFICATIONS

### Data & System Specifications
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `CACHE_SCHEMA.md` | docs/ | Data cache structure and schema documentation | ✅ Current |
| `DUCKDB_OPTIMIZATION.md` | docs/ | DuckDB optimization guide (10-20x performance improvement) | ✅ Current |
| `TRANSACTION_COSTS.md` | docs/ | Transaction cost model documentation (Dec 2025) | ✅ Current |
| `MASSIVE_INTEGRATION.md` | Root | Massive.com external data integration | ✅ Current |
| `SECTOR_ETF_INTEGRATION.md` | Root | Sector ETF system integration | ✅ Current |
| `SECTOR_ROTATION_GUIDE.md` | Root | Sector rotation mechanics and usage | ✅ Current |

**Recommendation:** Group data specs separately from integration specs.

---

## 5️⃣ CONFIGURATION & TESTING

### Configuration System
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `README.md` | configs/ | Configuration system usage guide - quick reference, file structure, creating custom configs, troubleshooting | ✅ Current (Updated Dec 10, 2025 - Restructured to focus on usage, added cross-reference to CONFIGURATION_STRATEGY_ANALYSIS.md) |
| `base_config.yaml` | configs/ | Production baseline (static stops, 1.0% risk, 6.0 threshold) | ✅ Active |
| `conservative_config.yaml` | configs/ | Capital preservation (1.0% risk, 6.5 threshold, no time stops) ⭐ RECOMMENDED | ✅ Active |
| `balanced_config.yaml` | configs/ | Most consistent across portfolio types (1.0% risk, 6.5 threshold, 20-bar time stops) ⭐ RECOMMENDED | ✅ Active |
| `aggressive_config.yaml` | configs/ | High risk approach (1.0% risk, 5.5 threshold, 8-bar time stops) ⚠️ NOT RECOMMENDED | ⚠️ Active (proven inferior in validation) |
| `time_decay_config.yamlx` | configs/ | Time decay stop strategy (experimental - NOT RECOMMENDED, 3x worse than static) | ⚠️ Research only (Updated Dec 10, 2025) |
| `vol_regime_config.yamlx` | configs/ | Volatility regime-adaptive stops (experimental - NOT RECOMMENDED, 32% stop rate) | ⚠️ Research only (Updated Dec 10, 2025) |
| `CONFIGURATION_STRATEGY_ANALYSIS.md` | docs/ | Deep empirical analysis across 6 portfolio types - decision framework for strategy selection | ✅ Current (Nov 2025, Updated Dec 10, 2025 - Added cross-reference to configs/README.md) |

**Status:** ✅ CONSOLIDATED - Two-tier structure implemented:
- **configs/README.md**: Usage guide for HOW to use configurations
- **docs/CONFIGURATION_STRATEGY_ANALYSIS.md**: Research document for WHY to choose configurations
- Strong cross-references added between both documents
- No content duplication - each serves distinct purpose

---

## 6️⃣ VALIDATION & ANALYSIS

### Master Validation Document
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `VALIDATION_MANUAL.md` | docs/ | ✅ **MASTER DOCUMENT** - Consolidated validation findings across all areas (entry signals, stop strategies, parameters, configs) | ✅ **AUTHORITATIVE** - Single source of truth (Created Dec 11, 2025) |

### Detailed Evidence Documents (Referenced by Manual)
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `STOP_STRATEGY_VALIDATION.md` | Root | ✅ VALIDATED stop strategy testing (Nov 22, 2025): Static wins by 3x, 982 trades | ✅ Detailed evidence - Referenced by VALIDATION_MANUAL |
| `VARIABLE_STOP_LOSS_FINDINGS.md` | Root | 🔬 PRELIMINARY stop loss research (Nov 16, 2025): Superseded findings | ⚠️ SUPERSEDED - Keep for historical reference |
| `STRATEGY_VALIDATION_COMPLETE.md` | Root | Entry signal validation (Nov 9, 2025): Moderate_Buy primary signal, 342 trades | ✅ Detailed evidence - Referenced by VALIDATION_MANUAL |
| `TIME_STOP_OPTIMIZATION_RESULTS.md` | Root | Time stop parameter optimization (Nov 22, 2025): 20 bars optimal | ✅ Detailed evidence - Referenced by VALIDATION_MANUAL |
| `CORRECTED_CONFIG_COMPARISON.md` | Root | Configuration comparison after signal filtering bug fix (Dec 9, 2025) | ✅ Detailed evidence - Referenced by VALIDATION_MANUAL |

### Supporting Documents
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `VALIDATION_STATUS.md` | docs/ | Living status dashboard - updated monthly with current validation status | ✅ Current (monthly updates) |
| `ANALYSIS_SCRIPTS_OVERLAP.md` | Root | Analysis script purposes and overlap assessment (Nov 22, 2025) | ✅ Current (assessment complete) |
| `REDUCE_TIME_STOP_RATE.md` | Root | Action plan for reducing time stop rate (Nov 22, 2025) | ✅ Current (action plan) |
| `PROFESSIONAL_ANALYSIS_PLAN.md` | Root | Professional metrics framework and implementation plan (Nov 22, 2025) | ✅ Current (framework document) |
| `HARDCODED_PARAMETERS_AUDIT.md` | docs/ | System-wide parameter audit | ✅ Current |

**Status:** ✅ CONSOLIDATED (Dec 11, 2025)
- **Solution**: Created docs/VALIDATION_MANUAL.md as master consolidation document
- **Structure**: 
  * Executive summary with all validated findings
  * 10 sections covering entry signals, stop strategies, parameters, configs, timeline, status, references
  * Links to detailed evidence documents for deep dives
  * Realistic performance expectations and trader recommendations
- **What's Consolidated**:
  * Entry signal validation (from STRATEGY_VALIDATION_COMPLETE.md)
  * Stop strategy validation (from STOP_STRATEGY_VALIDATION.md)
  * Parameter optimization (from TIME_STOP_OPTIMIZATION_RESULTS.md)
  * Configuration testing (from CORRECTED_CONFIG_COMPARISON.md)
  * Validation timeline showing Nov 16 vs Nov 22 contradiction resolution
- **Detailed Evidence Preserved**: All original validation documents kept for reference
- **Trading Decision**: Use static stops, Moderate_Buy (≥6.0), base_config or conservative_config

---

## 7️⃣ BUG FIXES & INCIDENTS

### Bug Fix Documentation
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `MA_CROSSDOWN_FIX_SUMMARY.md` | Root | MA_Crossdown parameter propagation fix (Dec 2025) | ✅ Resolved |
| `SIGNAL_FILTERING_FIX_SUMMARY.md` | Root | Critical signal filtering bug fix (Dec 2025) | ✅ Resolved |
| `NaN_BOOLEAN_FIX_DOCUMENTATION.md` | Root | Boolean handling fix for regime filters | ✅ Resolved |
| `REGIME_FILTER_FIX_IMPLEMENTATION.md` | Root | Regime filter implementation fix | ✅ Resolved |
| `THRESHOLD_DISCONNECT_FIX.md` | Root | Threshold configuration disconnect fix | ✅ Resolved |
| `CACHE_CORRUPTION_BUG_REPORT.md` | docs/ | Cache corruption incident and resolution | ✅ Resolved |
| `EXIT_TYPE_BUG_FIX.md` | upgrade-docs/ | Exit type bug fix | ✅ Resolved |

**Recommendation:** Archive to `docs/history/bug-fixes/` for reference, create "Lessons Learned" summary.

---

## 8️⃣ SESSION HISTORY & CHANGE LOG

### Development History
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `SESSION_IMPROVEMENTS_SUMMARY.md` | upgrade-docs/ | Running changelog of all sessions | ✅ Current |
| `SESSION_COMPLETE_NOV_2025.md` | upgrade-docs/ | November 2025 session summary | ✅ Historical |
| `upgrade_status.md` | upgrade-docs/ | Upgrade tracking (combined view) | ✅ Current |
| `upgrade_status_active.md` | upgrade-docs/ | Active upgrades | ✅ Current |
| `upgrade_status_completed.md` | upgrade-docs/ | Completed upgrades | ✅ Historical |
| `upgrade_spec.md` | upgrade-docs/ | Original upgrade specification | ✅ Reference |
| `upgrade_summary.md` | upgrade-docs/ | Upgrade summary | ✅ Current |
| `NEXT_SESSION_TASKS.md` | upgrade-docs/ | Future tasks and planning | ✅ Current |
| `PROJECT-STATUS.md` | Root | Current project status snapshot | ✅ Current |

**Recommendation:** Keep SESSION_IMPROVEMENTS_SUMMARY as authoritative changelog, archive session-specific docs.

---

## 9️⃣ IMPLEMENTATION SUMMARIES

### Feature Implementation Documentation
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `ITEM_5_IMPLEMENTATION_SUMMARY.md` | upgrade-docs/ | Item 5 implementation from upgrade spec | ✅ Historical |
| `ITEM_7_IMPLEMENTATION_SUMMARY.md` | upgrade-docs/ | Item 7 implementation from upgrade spec | ✅ Historical |
| `ITEM_11_IMPLEMENTATION_SUMMARY.md` | upgrade-docs/ | Item 11 implementation from upgrade spec | ✅ Historical |
| `ITEM_12_IMPLEMENTATION_SUMMARY.md` | upgrade-docs/ | Item 12 implementation from upgrade spec | ✅ Historical |
| `implementation_plan.md` | Root | Current implementation plan (Dec 2025) | ✅ Current |

**Recommendation:** Archive item summaries, link to relevant sections in main documentation.

---

## 🔟 TROUBLESHOOTING & SUPPORT

### Problem Solving Resources
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `TROUBLESHOOTING.md` | docs/ | Problem solving guide for common issues | ✅ Current |
| `tasks.md` | Root | Task tracking and TODO list | ✅ Active |

**Recommendation:** Expand troubleshooting with FAQ section, index by symptom.

---

## 1️⃣1️⃣ BACKTEST RESULTS & REPORTS

### Performance Reports & Analysis
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `professional_evaluation.txt` | Root | Current system evaluation (Grade A-, Sharpe 3.35) | ✅ Current |
| `professional_eval_20251206.txt` | Root | Historical performance report (Dec 6, 2025) | ✅ Historical |
| `professional_eval_20251207.txt` | Root | Performance report (Dec 7, 2025) | ✅ Historical |
| `professional_eval_20251207_ma_crossdown.txt` | Root | MA_Crossdown impact evaluation | ✅ Historical |
| `backtest_comparison_sp100_36mo.txt` | Root | S&P 100 two-run comparison (bull vs full cycle) | ✅ Historical (Dec 2025) |
| `backtest_comparison_all_three_configs.txt` | Root | Three-run analysis proving MA_Crossdown harmful | ✅ Historical (Dec 2025) |
| `portfolio_decomposition_analysis.txt` | Root | Portfolio size sensitivity analysis | ✅ Current |

**Recommendation:** Create `results/professional_reports/` directory, organize chronologically.

---

## 1️⃣2️⃣ REFERENCE DATA & METADATA

### Supporting Documentation
| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `README.md` | ticker_lists/ | Ticker list documentation and portfolio descriptions | ✅ Current |
| `sector_mappings.csv` | ticker_lists/ | Stock-to-sector ETF mappings (user-editable) | ✅ Current |
| `README.md` | Root | Main project README with quick start, commands, validation status | ✅ Current (Updated Dec 10, 2025 - Added Documentation Structure section, clarified variable stop validation timeline, added sector tools status note) |

**Status:** ✅ RESOLVED - Root README now includes documentation structure and links to inventory.

---

## 📑 ADDITIONAL FILES (Not Documentation)

### Discovered Non-Doc Files in Root
| File | Type | Purpose | Action |
|------|------|---------|--------|
| `tweaks.txt` | upgrade-docs/ | Design notes and parameter rationale | Consider incorporating into main docs |
| `refactor3.md` | Root | Refactoring notes | Archive or delete if obsolete |
| `report_simplification_tasks.md` | Root | Simplification task list | Incorporate into tasks.md or archive |
| `my-notes` | Root | Personal notes file | User private file |
| `cmb.txt` | Root | Unknown text file | Investigate purpose |
| `foo` | Root | Unknown file | Investigate purpose |

---

## 🎯 CATEGORIZATION ANALYSIS

### Documentation by Purpose:

**MUST HAVE (Critical for users):**
- TRADING_STRATEGY.md
- CODE_MAP.txt
- configs/README.md
- docs/USER_PLAYBOOK.md
- docs/TROUBLESHOOTING.md

**SHOULD HAVE (Important for understanding):**
- ARCHITECTURE_REFERENCE.md
- STOP_STRATEGY_VALIDATION.md
- CONFIGURATION_STRATEGY_ANALYSIS.md
- Various technical specs in docs/

**NICE TO HAVE (Historical/research):**
- Bug fix summaries
- Implementation summaries
- Historical backtest reports
- Session histories

**ARCHIVAL (Keep but move):**
- Completed bug fixes (7 files)
- Item implementation summaries (4 files)
- Session-specific histories
- Obsolete upgrade tracking

---

## 📊 OVERLAP ANALYSIS

### Identified Duplications:

1. **Architecture Documentation:** ✅ RESOLVED (Dec 10, 2025)
   - CODE_MAP.txt (quick reference, routing)
   - ARCHITECTURE_REFERENCE.md (conceptual overview)
   - **Action Taken:** Added cross-references, ensured complementary not duplicative

2. **Configuration Documentation:** ✅ CONSOLIDATED (Dec 10, 2025)
   - configs/README.md (usage guide)
   - CONFIGURATION_STRATEGY_ANALYSIS.md (empirical analysis)
   - **Action Taken:** Two-tier structure with strong cross-references
     * configs/README.md: Focus on usage (HOW)
     * docs/CONFIGURATION_STRATEGY_ANALYSIS.md: Focus on strategy selection (WHY)

3. **Strategy Documentation:** ✅ RESOLVED (Dec 10, 2025)
   - TRADING_STRATEGY.md (main)
   - SECTOR_ROTATION_ANALYSIS_GUIDE.md (formerly TRADING_STRATEGY_SECTOR_AWARE.md)
   - **Action Taken:** Renamed file, added status banner clarifying tools vs strategy

4. **Validation Documentation:** ⏳ PENDING
   - Multiple overlapping validation docs (10 files)
   - **Action:** Create single Validation Manual with chapters

5. **Exit Analysis:** ⏳ PENDING
   - Multiple files in upgrade-docs/
   - EXIT_ANALYSIS_*.md (3 files)
   - **Action:** Consolidate findings into main strategy doc

---

## 🔍 GAP ANALYSIS

### Missing Documentation:

**HIGH PRIORITY:**
1. **Quick Start Guide** - New users need onboarding
2. **API Reference** - For programmatic usage
3. **Migration Guide** - Between system versions
4. **Master Index** - Navigation tool (this doc will evolve into it)

**MEDIUM PRIORITY:**
5. **Performance Tuning Guide** - Scattered across multiple docs
6. **Risk Calculator Guide** - Position sizing walkthrough
7. **Deployment Guide** - Production deployment procedures
8. **Backup/Recovery Guide** - Data protection procedures

**LOW PRIORITY:**
9. **Development Guide** - For contributors
10. **Testing Guide** - For validation procedures
11. **Integration Guide** - For external systems
12. **Glossary** - Terms and definitions

---

## 📐 NAMING CONVENTION ANALYSIS

### Current Naming Patterns:

**SCREAMING_SNAKE_CASE (31 files):**
- Examples: `CODE_MAP.txt`, `TRADING_STRATEGY.md`, `STOP_STRATEGY_VALIDATION.md`
- Used for: Major documentation, high-level specs

**Title_Snake_Case (7 files):**
- Examples: `upgrade_status.md`, `upgrade_spec.md`
- Used for: Upgrade tracking docs

**lowercase_snake_case (8 files):**
- Examples: `session-close.md`, `git-workflow.md`, `tasks.md`
- Used for: Operational/workflow docs

**Inconsistency Issues:**
- No clear pattern for when to use which case
- Makes alphabetical sorting confusing
- Some files don't follow any convention

**Recommendation:** Standardize on SCREAMING_SNAKE_CASE for all markdown documentation.

---

## 🗂️ PROPOSED DIRECTORY STRUCTURE

```
docs/
├── user/                          # User-facing documentation
│   ├── QUICK_START.md            # NEW
│   ├── TRADING_STRATEGY.md       # Moved from root
│   ├── OPERATIONS_MANUAL.md      # Consolidated
│   ├── CONFIGURATION_GUIDE.md    # Consolidated
│   └── TROUBLESHOOTING.md        # Existing
│
├── technical/                     # Developer documentation
│   ├── ARCHITECTURE.md           # Consolidated
│   ├── API_REFERENCE.md          # NEW
│   ├── DATA_SYSTEMS.md           # Consolidated specs
│   ├── PERFORMANCE_TUNING.md     # NEW
│   └── TESTING_GUIDE.md          # NEW
│
├── research/                      # Analysis & validation
│   ├── VALIDATION_MANUAL.md      # Consolidated
│   ├── STOP_STRATEGY_RESEARCH.md # Consolidated
│   ├── PORTFOLIO_ANALYSIS.md     # Consolidated
│   └── PROFESSIONAL_METRICS.md   # Consolidated
│
└── history/                       # Historical/archival
    ├── bug-fixes/                # Bug fix summaries
    ├── implementations/          # Item implementation summaries
    ├── sessions/                 # Session histories
    └── reports/                  # Historical backtest reports
```

---

## ✅ NEXT STEPS

### Immediate Actions:
1. ✅ Create this inventory document
2. ⏳ Review inventory with stakeholders
3. ⏳ Prioritize consolidation targets
4. ⏳ Begin gap-filling (Quick Start Guide)
5. ⏳ Start directory reorganization

### Future Actions:
6. Create master documentation index (post-consolidation)
7. Implement naming convention standardization
8. Set up documentation review process
9. Create documentation templates
10. Establish update/maintenance schedule

---

## 📝 NOTES

- This inventory reflects the state as of December 10, 2025
- Files marked with ⚠️ need review or consolidation
- Files marked with ✅ are current and well-maintained
- Files marked with ❓ need investigation
- Historical files (✅ Historical) should be archived but kept accessible

**Maintenance:** Update this inventory as files are consolidated, moved, or created during the documentation reorganization project.

---

*End of Inventory*
