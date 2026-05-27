import json
import os
import pandas as pd
from visualization import Visualizer
from constants import *

# Color map for conflict types (moved out from function for reuse)
CONFLICT_COLOR_MAP = {
    "A1: left A, right A, conflict inside A": "#FF6B6B",
    "A2: left A, right B, conflict between A and B": "#F08A5D",
    "B2: one side A, other A-B, conflict between A and B": "#45B7D1",
    "D2: one side B, other A-B, conflict inside B": "#6D07EA",
    "F2: left A-B, right A-B, conflict inside B": "#2F3C7E",
    "A3: one side A, other B-C, conflict between A and C": "#7FDBB6",
    "C3: left A-C, right B-C, conflict inside C": "#B8B8FF",
    "D3: left A-B, right A-C, conflict between B and C": "#4ECDC4",
    "A4: left A-B, right C-D, conflict between B and D": "#C7CEEA",
    "Other cases": "#CCCCCC"
}

class ConflictAnalyzer:
    def __init__(self):
        self.visualizer = Visualizer()
        self.output_dir = '.'
    
    @staticmethod
    def _extract_dataset_label_from_path(path):
        """Extract dataset name from path like analysisReport/depth20RefDatasetSPARK/conflictsData/"""
        # Check for RefDataset or MergeDataset keywords in the path
        if 'RefDataset' in path:
            return 'Ref Dataset'
        elif 'MergeDataset' in path:
            return 'Merge Dataset'
        
        # Otherwise get the parent directory name (depth20RefDatasetSPARK, etc.)
        parent_dir = os.path.basename(os.path.dirname(path))
        # Try to extract dataset name from parent directory
        if 'RefDataset' in parent_dir:
            return 'Ref Dataset'
        elif 'MergeDataset' in parent_dir:
            return 'Merge Dataset'
        else:
            return parent_dir
        
    def analyze(self, plot=True, output_dir='.'):
        self.output_dir = output_dir
        df = pd.read_csv(os.path.join(output_dir, CONFLICT_STATS_CSV))
        conflicts = self._load_conflicts(output_dir)
        if df.empty:
            print("\nConflict Analysis Results:")
            print("No conflicts were found in the generated conflict statistics.")
            return
        self._print_statistics(df)
        
        # Write a detailed per-conflict type/structure report for debugging/validation
        try:
            report = self._build_conflict_explanations(conflicts)
            self._write_conflict_type_report(report, output_dir)
        except Exception:
            # avoid failing the whole analysis for report generation issues
            pass

        if plot:
            self._create_plots(df, conflicts=conflicts)
    
    def _print_statistics(self, df):
        self._print_conflict_stats(df, title=None)
    
    def _print_conflict_stats(self, df, title=None):
        """Print conflict statistics with optional title for comparison mode"""
        if title:
            print("-" * 60)
            print(f"\n{title}")
            print("-" * 60)
        else:
            print("\nConflict Analysis Results:")
        
        total_conflicts = len(df)
        total_scenarios = df[COL_SCENARIO_INDEX].nunique()
        same_depth_count = sum(df[COL_LEFT_LENGTH] == df[COL_RIGHT_LENGTH])
        same_class_count = sum(df[COL_SAME_CLASS])
        same_method_count = sum(df[COL_SAME_METHOD])        
        depth_mean = df[COL_DEPTH].mean()
        depth_median = df[COL_DEPTH].median()
        diff_mean = df[COL_DIFF].mean()
        diff_median = df[COL_DIFF].median()

        print(f"Total conflicts analyzed: {total_conflicts}")
        print(f"Conflicts with same depth: {same_depth_count} ({same_depth_count/total_conflicts*100:.2f}%)")
        print(f"Conflicts in same class: {same_class_count} ({same_class_count/total_conflicts*100:.2f}%)")
        print(f"Conflicts in same method: {same_method_count} ({same_method_count/total_conflicts*100:.2f}%)")
        
        print("\nDepth statistics:")
        print(f"  Mean depth: {depth_mean:.2f}")
        print(f"  Median depth: {depth_median:.2f}")

        print("\nStacktrace diff statistics:")
        print(f"  Mean diff: {diff_mean:.2f}")
        print(f"  Median diff: {diff_median:.2f}")

        print("\nConflicts per scenario distribution:")
        conflicts_per_scenario = df.groupby(COL_SCENARIO_INDEX).size()
        for num_conflicts in range(0, MAX_DEPTH + 1):
            count = sum(conflicts_per_scenario == num_conflicts)
            print(f"Scenarios with {num_conflicts} conflicts: {count} ({(count/total_scenarios*100):.2f}%)")
        
        print("\nConflict Depth Distribution:")

        for depth in range(0, MAX_DEPTH + 1):
            count = sum(df[COL_DEPTH] == depth)
            print(f"Conflicts with depth {depth}: {count} ({(count/total_conflicts*100):.2f}%)")

        print("\nConflicts diff Distribution:")
        for diff in range(0, 10):
            count = sum(df[COL_DIFF] == diff)
            print(f"Conflicts with diff {diff}: {count} ({(count/total_conflicts*100):.2f}%)")

    def _load_conflicts(self, output_dir):
        json_path = os.path.join(output_dir, JSON_INPUT_FILE)
        if not os.path.exists(json_path):
            return []

        with open(json_path, "r", encoding="utf-8") as json_file:
            payload = json.load(json_file)

        if isinstance(payload, dict):
            # build modified lines mapping for later processing
            self._build_modified_lines_map(payload)

            conflicts = payload.get("conflicts", [])
            return conflicts if isinstance(conflicts, list) else []

        return payload if isinstance(payload, list) else []

    @staticmethod
    def _extract_stack_files(interference):
        stack_trace = interference.get("stackTrace", [])
        files = []
        previous_file = None
        for frame in stack_trace:
            # ignore frames with invalid or negative line numbers
            line = frame.get('line')
            if line is None:
                continue
            try:
                if int(line) < 0:
                    continue
            except Exception:
                continue

            frame_file = ConflictAnalyzer._normalize_file_key(
                frame.get("file") or frame.get("location", {}).get("file") or frame.get("class")
            )
            if not frame_file:
                continue

            if frame_file != previous_file:
                files.append(frame_file)
                previous_file = frame_file

        # include location file only if it has a valid non-negative line
        loc = interference.get('location', {}) or {}
        loc_line = loc.get('line')
        try:
            if loc_line is not None and int(loc_line) >= 0:
                location_file = ConflictAnalyzer._normalize_file_key(loc.get('file'))
                if location_file and location_file != previous_file:
                    files.append(location_file)
        except Exception:
            pass

        return files

    @staticmethod
    def _normalize_file_key(value):
        if not value:
            return None
        lowers = value.lower()
        known_exts = ('.java', '.py', '.kt', '.scala', '.js', '.ts', '.c', '.cpp', '.h', '.cs')
        if any(lowers.endswith(ext) for ext in known_exts) or '/' in value or '\\' in value:
            return os.path.splitext(os.path.basename(value))[0]
        if "." in value and "/" not in value and "\\" not in value:
            return value.rsplit(".", 1)[-1]
        return os.path.splitext(os.path.basename(value))[0]

    def _build_modified_lines_map(self, payload):
        """Parse payload.modifiedLines into self.modified_lines_map."""
        modified = payload.get("modifiedLines", []) if isinstance(payload, dict) else []
        self.modified_lines_map = {}
        for entry in modified:
            fname = entry.get("file")
            if not fname:
                continue
            key = self._normalize_file_key(fname)
            self.modified_lines_map[key] = {
                'leftAdded': set(entry.get('leftAdded', []) or []),
                'leftRemoved': set(entry.get('leftRemoved', []) or []),
                'rightAdded': set(entry.get('rightAdded', []) or []),
                'rightRemoved': set(entry.get('rightRemoved', []) or []),
            }

    @staticmethod
    def _frame_line_valid(frame):
        """Return True if frame has a non-negative numeric line."""
        if frame is None:
            return False
        line = frame.get('line')
        if line is None:
            return False
        try:
            return int(line) >= 0
        except Exception:
            return False

    def _frame_file_key(self, frame):
        """Extract normalized file key from a frame dict."""
        file_val = frame.get("file") or frame.get("location", {}).get("file") or frame.get("class")
        return self._normalize_file_key(file_val)

    def _find_start_index(self, frames, branch):
        """Rule 1: start from first modified line by that branch's dev."""
        if not hasattr(self, 'modified_lines_map') or branch not in ('L', 'R'):
            return 0
        side = 'left' if branch == 'L' else 'right'
        for i, (fkey, line, fr) in enumerate(frames):
            if line is None or line == -1:
                continue
            entry = self.modified_lines_map.get(fkey)
            if not entry:
                continue
            if side == 'left' and (line in entry.get('leftAdded', set()) or line in entry.get('leftRemoved', set())):
                return i
            if side == 'right' and (line in entry.get('rightAdded', set()) or line in entry.get('rightRemoved', set())):
                return i
        return 0

    def _determine_owner(self, fkey, line, left_tuples, right_tuples):
        """Determine ownership ('L'/'R'/None) for a (file,line) tuple."""
        entry = getattr(self, 'modified_lines_map', {}).get(fkey)
        if entry:
            left_mod = line in entry.get('leftAdded', set())
            right_mod = line in entry.get('rightAdded', set())
            if left_mod and not right_mod:
                return 'L'
            if right_mod and not left_mod:
                return 'R'

        # fallback to closer in stack
        try:
            lpos = left_tuples.index((fkey, line))
            rpos = right_tuples.index((fkey, line))
            return 'L' if lpos < rpos else 'R'
        except ValueError:
            return None

    def _remove_tuple_from_frames(self, frames, fkey, line):
        return [frm for frm in frames if not (frm[0] == fkey and frm[1] == line)]

    def _frames_to_files(self, frames):
        files = []
        prev = None
        for fkey, ln, fr in frames:
            if fkey is None:
                continue
            if fkey == prev:
                continue
            files.append(fkey)
            prev = fkey
        return files

    def _files_for_classification(self, files_full):
        if len(files_full) > 2:
            return [files_full[0], files_full[-1]]
        return files_full

    def _out_path(self, output_dir, filename, compare=False):
        if compare and not filename.startswith('compare_'):
            return os.path.join(output_dir, 'compare_' + filename)
        return os.path.join(output_dir, filename)

    def _get_frames_with_lines(self, interference):
        """Return ordered list of (file_key, line, original_frame) tuples for an interference."""
        stack_trace = interference.get("stackTrace", [])
        frames = []
        previous = None
        for frame in stack_trace:
            # skip frames with invalid or negative line numbers
            if not self._frame_line_valid(frame):
                continue
            line = frame.get('line')

            file_key = self._frame_file_key(frame)
            if not file_key:
                continue

            # avoid consecutive duplicates of same file
            if file_key == previous:
                # still append as separate frame with line if different line
                if frames and frames[-1][0] == file_key and frames[-1][1] == line:
                    continue
            frames.append((file_key, line, frame))
            previous = file_key

        # include location file at the end if present
        loc = interference.get("location", {}) or {}
        loc_file = loc.get("file")
        if loc_file:
            loc_line = loc.get('line')
            try:
                if loc_line is not None and int(loc_line) >= 0:
                    lk = self._normalize_file_key(loc_file)
                    if not frames or frames[-1][0] != lk or frames[-1][1] != loc_line:
                        frames.append((lk, loc_line, {'location': loc}))
            except Exception:
                pass

        return frames

    def _process_interference_pair(self, left_interf, right_interf):
        """Apply modified-lines and duplicate-removal rules to a pair of interferences.

        Returns a dict with full lists and classification lists.
        """
        left_branch = left_interf.get('branch', '') if isinstance(left_interf, dict) else ''
        right_branch = right_interf.get('branch', '') if isinstance(right_interf, dict) else ''

        left_frames = self._get_frames_with_lines(left_interf)
        right_frames = self._get_frames_with_lines(right_interf)

        # Rule 1: start from first modified line by that branch's dev
        lstart = self._find_start_index(left_frames, left_branch)
        rstart = self._find_start_index(right_frames, right_branch)

        left_frames = left_frames[lstart:]
        right_frames = right_frames[rstart:]

        # Rule 2: remove repeated same (file,line) from the incorrect stack
        left_tuples = [(f, ln) for (f, ln, fr) in left_frames]
        right_tuples = [(f, ln) for (f, ln, fr) in right_frames]

        left_set = set(left_tuples)
        right_set = set(right_tuples)
        common = left_set.intersection(right_set)

        for t in common:
            fkey, line = t
            owner = self._determine_owner(fkey, line, left_tuples, right_tuples)
            if owner is None:
                continue

            # remove from the non-owner
            if owner == 'L':
                right_frames = self._remove_tuple_from_frames(right_frames, fkey, line)
                right_tuples = [(f, ln) for (f, ln, fr) in right_frames]
            else:
                left_frames = self._remove_tuple_from_frames(left_frames, fkey, line)
                left_tuples = [(f, ln) for (f, ln, fr) in left_frames]

        # Build file lists (full) preserving order and dedup consecutive same files
        left_files_full = self._frames_to_files(left_frames)
        right_files_full = self._frames_to_files(right_frames)

        return {
            'left_frames': left_frames,
            'right_frames': right_frames,
            'left_files_full': left_files_full,
            'right_files_full': right_files_full,
            'left_files_for_class': self._files_for_classification(left_files_full),
            'right_files_for_class': self._files_for_classification(right_files_full)
        }

    @staticmethod
    def _classify_conflict_type(left_files, right_files):
        left_count = len(left_files)
        right_count = len(right_files)

        if left_count == 1 and right_count == 1:
            return ConflictAnalyzer._classify_1_1(left_files, right_files)

        if left_count == 1 and right_count == 2:
            return ConflictAnalyzer._classify_1_2(left_files, right_files)

        if left_count == 2 and right_count == 1:
            return ConflictAnalyzer._classify_2_1(left_files, right_files)

        if left_count == 2 and right_count == 2:
            return ConflictAnalyzer._classify_2_2(left_files, right_files)

        return "Other cases"

    def _classify_1_1(left_files, right_files):
        return "A1: left A, right A, conflict inside A" if left_files[0] == right_files[0] else "A2: left A, right B, conflict between A and B"

    def _classify_1_2(left_files, right_files):
        if left_files[0] == right_files[0] and left_files[0] != right_files[-1]:
            return "B2: one side A, other A-B, conflict between A and B"
        if left_files[0] == right_files[-1]:
            return "D2: one side B, other A-B, conflict inside B"
        if left_files[0] != right_files[0] and left_files[0] != right_files[-1]:
            return "A3: one side A, other B-C, conflict between A and C"
        return "Other cases"

    def _classify_2_1(left_files, right_files):
        if right_files[0] == left_files[0] and left_files[-1] != right_files[0]:
            return "B2: one side A, other A-B, conflict between A and B"
        if right_files[0] == left_files[-1]:
            return "D2: one side B, other A-B, conflict inside B"
        if right_files[0] != left_files[0] and left_files[-1] != right_files[0]:
            return "A3: one side A, other B-C, conflict between A and C"
        return "Other cases"

    def _classify_2_2(left_files, right_files):
        left0, left1 = left_files[0], left_files[1]
        right0, right1 = right_files[0], right_files[1]
        left_set = set(left_files)
        right_set = set(right_files)

        # exact same last file
        if left1 == right1:
            if left0 == right0:
                return "F2: left A-B, right A-B, conflict inside B"
            return "C3: left A-C, right B-C, conflict inside C"

        # shared first file
        if left0 == right0:
            return "D3: left A-B, right A-C, conflict between B and C"

        # broader overlap: shared file across different positions
        if (left1 in right_set) or (left0 in right_set):
            return "D3: left A-B, right A-C, conflict between B and C"

        return "A4: left A-B, right C-D, conflict between B and D"

    def _get_conflict_type_distribution(self, df, conflicts=None):
        if conflicts is None:
            conflicts = []

        labels = []
        for conflict in conflicts:
            body = conflict.get("body", {}) if isinstance(conflict, dict) else {}
            interference = body.get("interference", []) if isinstance(body, dict) else []
            if not isinstance(interference, list) or len(interference) < 2:
                labels.append("Other cases")
                continue

            try:
                processed = self._process_interference_pair(interference[0], interference[1])
                left_files = processed.get('left_files_for_class', [])
                right_files = processed.get('right_files_for_class', [])
                labels.append(self._classify_conflict_type(left_files, right_files))
            except Exception:
                # fallback to original extraction
                left_files = self._extract_stack_files(interference[0])
                right_files = self._extract_stack_files(interference[1])
                labels.append(self._classify_conflict_type(left_files, right_files))

        if not labels:
            labels = ["Other cases"] * len(df)

        value_counts = pd.Series(labels).value_counts()
        total = len(labels)
        labels = value_counts.index.tolist()
        values = value_counts.values
        percentages = [(count / total) * 100 if total > 0 else 0 for count in values]
        
        # Use centralized color map
        colors = [CONFLICT_COLOR_MAP.get(label, "#CCCCCC") for label in labels]
        
        # Create a dict with all the pie chart data
        return {
            'values': values,
            'labels': labels,
            'percentages': percentages,
            'colors': colors
        }

    def _build_conflict_explanations(self, conflicts):
        """Return a list of dicts with detailed classification and structure for each conflict."""
        explanations = []
        for idx, conflict in enumerate(conflicts):
            explanations.append(self._explain_conflict(conflict, idx))

        return explanations

    def _explain_conflict(self, conflict, idx):
        body = conflict.get("body", {}) if isinstance(conflict, dict) else {}
        interference = body.get("interference", []) if isinstance(body, dict) else []
        if not isinstance(interference, list) or len(interference) < 2:
            return {
                "index": idx,
                "type": "Other cases",
                "reason": "invalid interference format",
                "left_files": [],
                "right_files": [],
                "left_stack": [],
                "right_stack": [],
            }

        try:
            proc = self._process_interference_pair(interference[0], interference[1])
            left_files_full = proc.get('left_files_full', [])
            right_files_full = proc.get('right_files_full', [])
            left_files_for_class = proc.get('left_files_for_class', [])
            right_files_for_class = proc.get('right_files_for_class', [])
            ctype = self._classify_conflict_type(left_files_for_class, right_files_for_class)

            return {
                "index": idx,
                "type": ctype,
                "left_files_full": left_files_full,
                "right_files_full": right_files_full,
                "left_files_for_class": left_files_for_class,
                "right_files_for_class": right_files_for_class,
                "left_stack": [f for (_, _, f) in proc.get('left_frames', [])],
                "right_stack": [f for (_, _, f) in proc.get('right_frames', [])],
                "reason": f"start_trimmed_from_modified_lines; left_count_full={len(left_files_full)}, right_count_full={len(right_files_full)}",
            }
        except Exception:
            left_files = self._extract_stack_files(interference[0])
            right_files = self._extract_stack_files(interference[1])
            ctype = self._classify_conflict_type(left_files, right_files)
            return {
                "index": idx,
                "type": ctype,
                "left_files": left_files,
                "right_files": right_files,
                "left_stack": interference[0].get("stackTrace", []),
                "right_stack": interference[1].get("stackTrace", []),
                "reason": f"fallback classification: left_count={len(left_files)}, right_count={len(right_files)}",
            }

    def _write_conflict_type_report(self, report, output_dir):
        """Write the conflict type explanations to a JSON file for debugging/validation."""
        try:
            out_path = os.path.join(output_dir, "conflict_types_report.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception:
            # keep non-fatal
            pass

    def _get_boolean_pie_data(self, df, column, true_label='True', false_label='False'):

        true_count = int(df[column].sum())
        false_count = int((~df[column]).sum())
        total = len(df)

        labels = [true_label, false_label]
        values = [true_count, false_count]
        percentages = [ (true_count/total)*100 if total>0 else 0,
                        (false_count/total)*100 if total>0 else 0 ]

        return {
            'values': values,
            'labels': labels,
            'percentages': percentages,
            'colors': ['steelblue', 'coral']
        }

    def _create_plots(self, df, conflicts=None):
        self._create_all_plots(df, conflicts=conflicts)

    def _create_all_plots(self, df, compare_df=None, label1='Data 1', label2='Data 2', output_dir=None, conflicts=None, compare_conflicts=None):
        """Generic method to create all plots in single or comparison mode"""
        if output_dir is None:
            output_dir = self.output_dir
        
        # Depth loss bar charts
        self._plot_depth_loss(df, output_dir, compare_df, label1, label2)
        
        # Histograms
        self._plot_histograms(df, output_dir, compare_df, label1, label2)
        
        # Line plots
        self._plot_depth_lines(df, output_dir, compare_df, label1, label2)
        
        # Pie charts (comparison or single)
        self._plot_pie_charts(df, output_dir, compare_df, label1, label2, conflicts=conflicts, compare_conflicts=compare_conflicts)

    def _plot_depth_loss(self, df, output_dir, compare_df=None, label1='Data 1', label2='Data 2'):
        """Plot depth loss - bar chart (single or comparison)"""
        total_conflicts = len(df)
        depths = list(range(DEFAULT_DEPTH, MAX_DEPTH + 1))
        loss_percentages = [(sum(df[COL_DEPTH] > depth) / total_conflicts * 100) for depth in depths]
        
        if compare_df is not None:
            total_conflicts2 = len(compare_df)
            loss_percentages2 = [(sum(compare_df[COL_DEPTH] > depth) / total_conflicts2 * 100) for depth in depths]
            
            self.visualizer.plot_bar_chart_compare(
                x=depths,
                y1=loss_percentages,
                y2=loss_percentages2,
                label1=label1,
                label2=label2,
                title='Percentage of Conflicts Lost per Depth',
                xlabel='Depth',
                ylabel='Conflicts Lost (%)',
                filename=self._out_path(output_dir, PLOT_DEPTH_LOSS, compare=True)
            )
        else:
            self.visualizer.plot_bar_chart(
                x=depths,
                y=loss_percentages,
                title='Percentage of Conflicts Lost per Depth',
                xlabel='Depth',
                ylabel='Conflicts Lost (%)',
                filename=self._out_path(output_dir, PLOT_DEPTH_LOSS)
            )

    def _plot_histograms(self, df, output_dir, compare_df=None, label1='Data 1', label2='Data 2'):
        """Plot all histograms - depth, diff, etc."""
        # Depth distribution (discrete values - use side-by-side bars)
        self._plot_distribution_bars(
            df=df, compare_df=compare_df, col=COL_DEPTH, 
            max_val=MAX_DEPTH, title='Conflict Depth Distribution', 
            xlabel='Depth', filename=PLOT_DEPTH_HIST,
            output_dir=output_dir, label1=label1, label2=label2
        )
        
        # Diff distribution (discrete values up to 10 - use side-by-side bars)
        self._plot_distribution_bars(
            df=df, compare_df=compare_df, col=COL_DIFF,
            max_val=10, title='Conflicts Diff Distribution',
            xlabel='Absolute difference (L-R)', filename=PLOT_DIFF_HIST,
            output_dir=output_dir, label1=label1, label2=label2
        )
        
        # Conflicts per scenario with bucketing
        conflicts_per_scenario = df.groupby(COL_SCENARIO_INDEX).size()
        
        if compare_df is not None:
            conflicts_per_scenario2 = compare_df.groupby(COL_SCENARIO_INDEX).size()
            self.visualizer.plot_conflicts_per_scenario_compare(
                data1=conflicts_per_scenario,
                data2=conflicts_per_scenario2,
                title='Number of Conflicts per Scenario',
                label1=label1,
                label2=label2,
                filename=os.path.join(output_dir, 'compare_' + PLOT_CONFLICTS_PER_SCENARIO)
            )
        else:
            self.visualizer.plot_histogram(
                data=conflicts_per_scenario,
                bins=100,
                title='Number of Conflicts per Scenario',
                xlabel='Number of Conflicts',
                filename=os.path.join(output_dir, PLOT_CONFLICTS_PER_SCENARIO)
            )
        
        # Filtered histograms (only in single mode)
        if compare_df is None:
            same_class_df = df[df[COL_SAME_CLASS] == False]
            self.visualizer.plot_histogram(
                data=same_class_df[COL_DEPTH],
                bins=30,
                title='Different Class Conflicts Histogram of Depths',
                xlabel='Depths',
                filename=os.path.join(output_dir, PLOT_DIFFERENT_CLASS_DEPTH_HIST)
            )

            same_method_df = df[df[COL_SAME_METHOD] == False]
            self.visualizer.plot_histogram(
                data=same_method_df[COL_DEPTH],
                bins=30,
                title='Different Method Conflicts Histogram of Depths',
                xlabel='Depths',
                filename=os.path.join(output_dir, PLOT_DIFFERENT_METHOD_DEPTH_HIST)
            )

            conflicts_per_jar = df.groupby(COL_SCENARIO_JAR).size()
            self.visualizer.plot_histogram(
                data=conflicts_per_jar,
                bins=100,
                title='Number of Conflicts per ScenarioJAR',
                xlabel='Number of Conflicts',
                filename=os.path.join(output_dir, PLOT_CONFLICTS_PER_JAR)
            )

    def _plot_distribution_bars(self, df, col, max_val, title, xlabel, filename, output_dir, 
                                compare_df=None, label1='Data 1', label2='Data 2'):
        """Plot discrete distribution as side-by-side bars for comparison or single bar chart"""
        x_vals = list(range(0, max_val + 1))
        counts1 = [sum(df[col] == val) for val in x_vals]
        total1 = len(df)
        percentages1 = [(count / total1 * 100) if total1 > 0 else 0 for count in counts1]
        
        if compare_df is not None:
            counts2 = [sum(compare_df[col] == val) for val in x_vals]
            total2 = len(compare_df)
            percentages2 = [(count / total2 * 100) if total2 > 0 else 0 for count in counts2]
            
            self.visualizer.plot_bar_chart_compare(
                x=x_vals,
                y1=percentages1,
                y2=percentages2,
                label1=label1,
                label2=label2,
                title=title,
                xlabel=xlabel,
                ylabel='Percentage (%)',
                filename=self._out_path(output_dir, filename, compare=True)
            )
        else:
            self.visualizer.plot_bar_chart(
                x=x_vals,
                y=percentages1,
                title=title,
                xlabel=xlabel,
                ylabel='Percentage (%)',
                filename=self._out_path(output_dir, filename)
            )

    def _plot_depth_lines(self, df, output_dir, compare_df=None, label1='Data 1', label2='Data 2'):
        """Plot conflict depth lines"""
        if compare_df is not None:
            self.visualizer.plot_conflict_depth_lines_compare(
                df1=df,
                df2=compare_df,
                title='Conflict Depths Behavior',
                label1=label1,
                label2=label2,
                filename=self._out_path(output_dir, PLOT_DEPTH_LINES, compare=True)
            )
        else:
            self.visualizer.plot_conflict_depth_lines(
                df=df,
                title='Conflict Depths Behavior',
                filename=self._out_path(output_dir, PLOT_DEPTH_LINES)
            )

    def _plot_pie_charts(self, df, output_dir, compare_df=None, label1='Data 1', label2='Data 2', conflicts=None, compare_conflicts=None):
        """Plot pie charts - conflict types and boolean data"""
        # Conflict type distribution
        if compare_df is not None:
            data1 = self._get_conflict_type_distribution(df, conflicts=conflicts)
            data2 = self._get_conflict_type_distribution(compare_df, conflicts=compare_conflicts)
            self.visualizer.plot_pie_chart_compare(
                data1=data1,
                data2=data2,
                title1=f'{label1} - Conflict Types',
                title2=f'{label2} - Conflict Types',
                filename=self._out_path(output_dir, PLOT_TYPES_HIST, compare=True)
            )
            self._create_compare_pie_charts(df, compare_df, label1, label2, output_dir)
        else:
            self.visualizer.plot_pie_chart(
                data=self._get_conflict_type_distribution(df, conflicts=conflicts),
                title='Distribution of Conflict Types',
                filename=self._out_path(output_dir, PLOT_TYPES_HIST)
            )
            
            same_class_data = self._get_boolean_pie_data(df, COL_SAME_CLASS, true_label='Same class', false_label='Different class')
            self.visualizer.plot_pie_chart(
                data=same_class_data,
                title='Proportion of Conflicts in Same Class',
                filename=self._out_path(output_dir, PLOT_SAME_CLASS_PIE)
            )

            same_method_data = self._get_boolean_pie_data(df, COL_SAME_METHOD, true_label='Same method', false_label='Different method')
            self.visualizer.plot_pie_chart(
                data=same_method_data,
                title='Proportion of Conflicts in Same Method',
                filename=self._out_path(output_dir, PLOT_SAME_METHOD_PIE)
            )

    def analyze_compare(self, plot=True, output_dir='.', output_dir2='.', label1=None, label2=None):
        """Analyze and compare two JSON file results"""
        df1 = pd.read_csv(os.path.join(output_dir, CONFLICT_STATS_CSV))
        df2 = pd.read_csv(os.path.join(output_dir2, CONFLICT_STATS_CSV))
        conflicts1 = self._load_conflicts(output_dir)
        conflicts2 = self._load_conflicts(output_dir2)
        
        # Use provided labels, otherwise extract dataset names from paths
        if label1 is None:
            label1 = self._extract_dataset_label_from_path(output_dir)
        if label2 is None:
            label2 = self._extract_dataset_label_from_path(output_dir2)
        
        self._print_conflict_stats(df1, title=label1)
        print("\n" + "="*60)
        self._print_conflict_stats(df2, title=label2)
        
        if plot:
            self._create_compare_plots(df1, df2, label1, label2, output_dir, conflicts1=conflicts1, conflicts2=conflicts2)

    def _print_statistics_with_title(self, df, title):
        self._print_conflict_stats(df, title=title)

    def _create_compare_plots(self, df1, df2, label1, label2, output_dir, conflicts1=None, conflicts2=None):
        """Create comparison plots for two datasets"""
        self._create_all_plots(
            df1,
            compare_df=df2,
            label1=label1,
            label2=label2,
            output_dir=output_dir,
            conflicts=conflicts1,
            compare_conflicts=conflicts2,
        )

    def analyze_compare_multiple(self, plot=True, output_dirs=None, labels=None):
        """Print conflict stats for N datasets. Plots are not generated for N > 2."""
        output_dirs = output_dirs or []
        labels = labels or []

        for i, output_dir in enumerate(output_dirs):
            df = pd.read_csv(os.path.join(output_dir, CONFLICT_STATS_CSV))
            label = labels[i] if i < len(labels) else f"Dataset {i + 1}"
            if i > 0:
                print("\n" + "=" * 60)
            self._print_conflict_stats(df, title=label)

    def _create_compare_pie_charts(self, df1, df2, label1, label2, output_dir):
        """Create side-by-side pie chart comparisons"""
        pie_configs = [
            (COL_SAME_CLASS, 'Same class', 'Different class', PLOT_SAME_CLASS_PIE, 'Same Class'),
            (COL_SAME_METHOD, 'Same method', 'Different method', PLOT_SAME_METHOD_PIE, 'Same Method')
        ]
        
        for col, true_label, false_label, filename, title_suffix in pie_configs:
            data1 = self._get_boolean_pie_data(df1, col, true_label=true_label, false_label=false_label)
            data2 = self._get_boolean_pie_data(df2, col, true_label=true_label, false_label=false_label)
            
            self.visualizer.plot_pie_chart_compare(
                data1=data1,
                data2=data2,
                title1=f'{label1} - {title_suffix}',
                title2=f'{label2} - {title_suffix}',
                filename=self._out_path(output_dir, filename, compare=True)
            )