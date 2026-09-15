"""Seeds the in-memory store with demo data so the frontend has something to
show immediately after the backend starts, with no manual setup.

Seeded accounts (all use the password `password123`):

  alice@example.com  - admin on "Website Redesign", member on "Mobile App"
  bob@example.com    - member on "Website Redesign", admin on "Mobile App"
  carol@example.com  - viewer on "Website Redesign"
  dave@example.com   - no project membership; has a pending invitation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from . import auth
from .models import (
    Activity,
    Attachment,
    Board,
    Column,
    Comment,
    Invitation,
    InvitationStatus,
    Label,
    Priority,
    Project,
    ProjectMember,
    Provider,
    Role,
    Task,
    TaskType,
    User,
    utcnow_iso,
)
from .store import Store, new_id

DEFAULT_COLUMN_NAMES = ["To Do", "In Progress", "Review", "Done"]
DEMO_PASSWORD = "password123"


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def create_default_board(db: Store, project_id: str, name: str, now: datetime | None = None) -> Board:
    created_at = _iso(now) if now is not None else utcnow_iso()
    board = Board(id=new_id("board"), projectId=project_id, name=name, createdAt=created_at)
    db.boards[board.id] = board
    for position, col_name in enumerate(DEFAULT_COLUMN_NAMES):
        column = Column(id=new_id("col"), boardId=board.id, name=col_name, position=position)
        db.columns[column.id] = column
    return board


def seed_demo_data(db: Store) -> None:
    now = datetime.now(UTC)

    def make_user(name: str, email: str, color: str) -> User:
        user = User(
            id=new_id("user"),
            name=name,
            email=email,
            avatarColor=color,
            provider=Provider.password,
            createdAt=_iso(now),
        )
        db.users[user.id] = user
        db.credentials[user.id] = auth.hash_password(DEMO_PASSWORD)
        return user

    alice = make_user("Alice Anderson", "alice@example.com", "#f97316")
    bob = make_user("Bob Baker", "bob@example.com", "#3b82f6")
    carol = make_user("Carol Chen", "carol@example.com", "#10b981")
    make_user("Dave Diaz", "dave@example.com", "#a855f7")

    # -- Project 1: Website Redesign ----------------------------------
    web = Project(
        id=new_id("proj"),
        key="WEB",
        name="Website Redesign",
        description="Revamp the public marketing site.",
        createdBy=alice.id,
        createdAt=_iso(now),
    )
    db.projects[web.id] = web
    for user, role in [(alice, Role.admin), (bob, Role.member), (carol, Role.viewer)]:
        m = ProjectMember(id=new_id("mem"), projectId=web.id, userId=user.id, role=role, createdAt=_iso(now))
        db.members[m.id] = m

    web_board = create_default_board(db, web.id, "Main Board", now)
    web_columns = db.list_columns(web_board.id)
    todo, in_progress, review, done = web_columns

    label_frontend = Label(id=new_id("label"), projectId=web.id, name="frontend", color="#3b82f6")
    label_backend = Label(id=new_id("label"), projectId=web.id, name="backend", color="#8b5cf6")
    label_bug = Label(id=new_id("label"), projectId=web.id, name="bug", color="#ef4444")
    label_urgent = Label(id=new_id("label"), projectId=web.id, name="urgent", color="#f97316")
    for label in (label_frontend, label_backend, label_bug, label_urgent):
        db.labels[label.id] = label

    def make_task(
        column: Column,
        position: int,
        title: str,
        *,
        description: str = "",
        type_: TaskType = TaskType.task,
        priority: Priority = Priority.medium,
        assignee: User | None = None,
        label_ids: list[str] | None = None,
        due_in_days: int | None = None,
        created_by: User = alice,
    ) -> Task:
        due_date = _iso(now + timedelta(days=due_in_days)) if due_in_days is not None else None
        task = Task(
            id=new_id("task"),
            key=f"{web.key}-{db.next_task_number(web.id)}",
            projectId=web.id,
            boardId=web_board.id,
            columnId=column.id,
            title=title,
            description=description,
            type=type_,
            priority=priority,
            assigneeId=assignee.id if assignee else None,
            labelIds=label_ids or [],
            dueDate=due_date,
            position=position,
            createdBy=created_by.id,
            createdAt=_iso(now),
            updatedAt=_iso(now),
        )
        db.tasks[task.id] = task
        activity = Activity(
            id=new_id("act"),
            projectId=web.id,
            taskId=task.id,
            actorId=created_by.id,
            message=f'{created_by.name} created {task.key}',
            createdAt=_iso(now),
        )
        db.activities[activity.id] = activity
        return task

    t1 = make_task(
        todo,
        0,
        "Fix login validation",
        description="Login validation fails when the email has a trailing space.",
        type_=TaskType.bug,
        priority=Priority.high,
        assignee=bob,
        label_ids=[label_frontend.id, label_bug.id],
        due_in_days=-2,
    )
    make_task(
        todo,
        1,
        "Add search to task list",
        type_=TaskType.feature,
        priority=Priority.medium,
        assignee=carol,
        label_ids=[label_frontend.id],
        due_in_days=7,
    )
    make_task(
        in_progress,
        0,
        "Update API rate limiting",
        type_=TaskType.task,
        priority=Priority.urgent,
        assignee=alice,
        label_ids=[label_backend.id, label_urgent.id],
        due_in_days=1,
    )
    make_task(
        in_progress,
        1,
        "Redesign project settings page",
        type_=TaskType.feature,
        priority=Priority.low,
        assignee=bob,
        label_ids=[label_frontend.id],
    )
    make_task(
        review,
        0,
        "Payment validation edge cases",
        type_=TaskType.bug,
        priority=Priority.high,
        assignee=alice,
        label_ids=[label_backend.id, label_bug.id],
    )
    make_task(
        done,
        0,
        "Set up CI pipeline",
        type_=TaskType.task,
        priority=Priority.medium,
        assignee=bob,
    )

    comment1 = Comment(
        id=new_id("comment"),
        taskId=t1.id,
        authorId=bob.id,
        body="I found the problem in the email normalization step.",
        createdAt=_iso(now),
        updatedAt=_iso(now),
    )
    db.comments[comment1.id] = comment1
    db.activities[new_id("act")] = Activity(
        id=new_id("act"),
        projectId=web.id,
        taskId=t1.id,
        actorId=bob.id,
        message=f"{bob.name} commented on {t1.key}",
        createdAt=_iso(now),
    )

    db.attachments[new_id("att")] = Attachment(
        id=new_id("att"),
        taskId=t1.id,
        filename="error.png",
        fileType="image/png",
        fileSize=48213,
        uploadedBy=bob.id,
        uploadedAt=_iso(now),
        storageUrl=f"/uploads/{new_id('file')}.png",
    )

    invitation = Invitation(
        id=new_id("inv"),
        projectId=web.id,
        email="dave@example.com",
        role=Role.member,
        status=InvitationStatus.pending,
        invitedBy=alice.id,
        createdAt=_iso(now),
    )
    db.invitations[invitation.id] = invitation

    # -- Project 2: Mobile App -----------------------------------------
    mobile = Project(
        id=new_id("proj"),
        key="MOB",
        name="Mobile App",
        description="Native companion app for the platform.",
        createdBy=bob.id,
        createdAt=_iso(now),
    )
    db.projects[mobile.id] = mobile
    for user, role in [(bob, Role.admin), (alice, Role.member)]:
        m = ProjectMember(
            id=new_id("mem"), projectId=mobile.id, userId=user.id, role=role, createdAt=_iso(now)
        )
        db.members[m.id] = m

    mobile_board = create_default_board(db, mobile.id, "Main Board", now)
    mobile_todo = db.list_columns(mobile_board.id)[0]

    def make_mobile_task(position: int, title: str, **kwargs) -> Task:
        task = Task(
            id=new_id("task"),
            key=f"{mobile.key}-{db.next_task_number(mobile.id)}",
            projectId=mobile.id,
            boardId=mobile_board.id,
            columnId=mobile_todo.id,
            title=title,
            position=position,
            createdBy=bob.id,
            createdAt=_iso(now),
            updatedAt=_iso(now),
            **kwargs,
        )
        db.tasks[task.id] = task
        return task

    make_mobile_task(0, "Set up React Native project", assigneeId=bob.id, priority=Priority.high)
    make_mobile_task(1, "Design onboarding flow", assigneeId=alice.id, type=TaskType.feature)
