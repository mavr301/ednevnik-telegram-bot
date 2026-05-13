from collections import defaultdict
from typing import Dict, List, Tuple

from scraper import Grade


def _grade_emoji(g: int) -> str:
    return {5: "⭐", 4: "🟢", 3: "🟡", 2: "🟠", 1: "🔴"}.get(g, "❓")


def format_single_grade(grade: Grade) -> str:
    if grade.is_note:
        lines = [
            f"📚 {grade.subject}",
            f"📅 {grade.date}  📝 Note",
            f"💬 {grade.comment}",
        ]
    else:
        emoji = _grade_emoji(grade.grade)
        lines = [
            f"📚 {grade.subject}",
            f"📅 {grade.date}  {emoji} {grade.grade}",
        ]
        if grade.comment:
            lines.append(f"📝 {grade.comment}")
    return "\n".join(lines)


def format_new_grades(grades: List[Grade]) -> str:
    if not grades:
        return "No new marks."
    if len(grades) == 1:
        return f"📬 New mark\n\n{format_single_grade(grades[0])}"
    parts = [f"📬 {len(grades)} new marks"]
    for g in grades:
        parts.append("")
        parts.append(format_single_grade(g))
    return "\n".join(parts)


def format_subject(subject: str, teacher: str, grades: List[Grade]) -> str:
    if not grades:
        return f"📚 {subject}\nNo marks yet."

    header = f"📚 {subject}"
    if teacher:
        header += f" — {teacher}"

    lines = [header, "─" * 32]
    for g in grades:
        if g.is_note:
            line = f"{g.date:<8} 📝   {g.comment}"
        else:
            emoji = _grade_emoji(g.grade)
            line = f"{g.date:<8} {emoji} {g.grade}"
            if g.comment:
                line += f"   {g.comment}"
        lines.append(line)

    lines.append("─" * 32)
    graded = [g for g in grades if not g.is_note]
    if graded:
        avg = sum(g.grade for g in graded) / len(graded)
        lines.append(f"Average: {avg:.1f}  ·  {len(graded)} marks  ·  {len(grades) - len(graded)} notes")
    else:
        lines.append(f"{len(grades)} notes, no numeric marks yet")
    return "\n".join(lines)


def format_all_by_subject(all_grades: List[Grade]) -> List[str]:
    """Returns one formatted message string per subject, sorted alphabetically."""
    by_subject: Dict[str, List[Grade]] = defaultdict(list)
    teachers: Dict[str, str] = {}

    for g in all_grades:
        by_subject[g.subject].append(g)
        if g.teacher:
            teachers[g.subject] = g.teacher

    messages = []
    for subject in sorted(by_subject.keys()):
        grades = by_subject[subject]
        teacher = teachers.get(subject, "")
        messages.append(format_subject(subject, teacher, grades))
    return messages


def format_averages(all_grades: List[Grade]) -> str:
    if not all_grades:
        return "No marks found."

    by_subject: Dict[str, List[Grade]] = defaultdict(list)
    for g in all_grades:
        by_subject[g.subject].append(g)

    avgs: List[Tuple[str, float]] = [
        (s, sum(g.grade for g in gs if not g.is_note) / max(len([g for g in gs if not g.is_note]), 1))
        for s, gs in by_subject.items()
        if any(not g.is_note for g in gs)
    ]
    avgs.sort(key=lambda x: x[1], reverse=True)

    lines = ["📊 Averages\n"]
    for subject, avg in avgs:
        emoji = _grade_emoji(round(avg))
        lines.append(f"{emoji} {avg:.1f}  ·  {subject}")
    return "\n".join(lines)
