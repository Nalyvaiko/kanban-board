# Mini Jira Kanban — MVP Project Scope

## 1. Project Overview

A Jira-style project management application focused on a clean Kanban workflow.

Users can create and manage multiple projects, organize work on customizable Kanban boards, assign tasks to team members, track progress, comment on tasks, upload attachments, and view activity history.

The goal is to build a **realistic mini-Jira application**, not a simple demo Kanban board.

---

# 2. MVP Goals

The MVP must allow users to:

* Create an account
* Log in with email/password
* Log in with Google
* Create and manage multiple projects
* Add users to projects
* Invite users by email
* Create Kanban boards
* Customize board columns
* Create, edit, and delete tasks
* Assign tasks to users
* Set priorities
* Set task types
* Add labels
* Set optional due dates
* Drag tasks between columns
* Change task status from task details
* Add comments
* Edit/delete own comments
* Upload task attachments
* Link related tasks
* Search and filter tasks
* View Kanban and List views
* View automatic activity history
* See assigned and overdue tasks from the dashboard

---

# 3. Application Structure

```text
User
 └── Projects
      └── Boards
           └── Columns
                └── Tasks
```

Users can belong to multiple projects.

A project can have multiple users and boards.

---

# 4. User Roles

The MVP has three roles.

## Admin

Can:

* Create projects
* Edit projects
* Delete projects
* Manage project members
* Invite users
* Manage project labels
* Create/edit/delete board columns
* Create/edit/delete tasks
* Assign tasks
* Manage all project data

## Member

Can:

* View projects they belong to
* Create tasks
* Edit tasks
* Move tasks
* Assign tasks where permitted
* Add labels
* Add comments
* Edit/delete their own comments
* Upload attachments
* View activity history

## Viewer

Can:

* View projects
* View boards
* View tasks
* Search and filter
* View comments
* View attachments
* View activity history

Viewer cannot modify project data.

---

# 5. Authentication

## Supported authentication

* Email + password
* Google login

## MVP authentication features

* Registration
* Login
* Logout
* Protected application routes
* Current-user/session handling

Password reset is optional and can be added after the core MVP.

---

# 6. Projects

Users can belong to multiple projects.

Each project contains:

* Project name
* Description
* Members
* Roles
* Boards
* Labels
* Tasks

## Project management

Admins can:

* Create project
* Edit project
* Delete project
* Add existing users
* Invite users by email
* Remove project members
* Change member roles

---

# 7. Boards

Each project can contain one or more Kanban boards.

A board contains customizable columns.

Example default board:

```text
To Do → In Progress → Review → Done
```

## Board columns

Project admins can:

* Create columns
* Rename columns
* Delete columns
* Reorder columns

Columns are not hard-coded.

---

# 8. Tasks

Tasks are the primary work item.

Each task contains:

```text
ID
Title
Description
Type
Status
Priority
Assignee
Labels
Due Date
Project
Board
Column
Created By
Created At
Updated At
```

---

# 9. Task Types

The MVP supports:

* Task
* Bug
* Feature

Example:

```text
TASK-101
Fix login validation
Type: Bug
```

---

# 10. Priorities

The MVP supports four priorities:

* Low
* Medium
* High
* Urgent

---

# 11. Labels

Labels are managed at the project level.

Project admins can:

* Create labels
* Rename labels
* Delete labels

Members can assign existing labels to tasks.

Example:

```text
frontend
backend
bug
urgent
database
```

---

# 12. Due Dates

Tasks can have an optional due date.

A task may have:

```text
Due date: September 20, 2026
```

or no due date.

Overdue tasks should be identifiable on the dashboard.

---

# 13. Task Assignment

Tasks can be assigned to project members.

Example:

```text
Task: Fix payment API
Assignee: John Smith
```

A task can have one assignee in the MVP.

---

# 14. Kanban Board

The main project screen is the Kanban board.

Example:

```text
┌──────────┐  ┌─────────────┐  ┌────────┐  ┌──────┐
│ To Do    │  │ In Progress │  │ Review │  │ Done │
├──────────┤  ├─────────────┤  ├────────┤  ├──────┤
│ Task 101 │  │ Task 104    │  │ Task   │  │ Task │
│ Task 102 │  │ Task 105    │  │ 108    │  │ 109  │
│ Task 103 │  │             │  │        │  │      │
└──────────┘  └─────────────┘  └────────┘  └──────┘
```

---

# 15. Task Movement

Users can change task status in two ways:

## Drag & Drop

Drag a task from one column to another.

Example:

```text
To Do
  ↓
Drag Task
  ↓
In Progress
```

## Task Details

The user can open the task and change its status manually.

Both methods must update the task status.

---

# 16. Task Details

Clicking a task opens a task details screen/modal.

Example:

```text
TASK-123

Fix login validation

Type: Bug
Priority: High
Status: In Progress
Assignee: John
Due: Sep 20

Labels:
[frontend] [authentication]

Description
----------------
Login validation fails when...

Comments
----------------
John:
I found the problem in the API.

Attachments
----------------
error.png

Activity
----------------
John moved task from To Do → In Progress
```

---

# 17. Comments

Users can add comments to tasks.

MVP functionality:

* Add comment
* Edit own comment
* Delete own comment
* View comments

No threaded comments or reactions in MVP.

---

# 18. Attachments

Users can upload files to tasks.

Each attachment should contain:

```text
Filename
File type
File size
Uploaded by
Uploaded at
Storage location
```

MVP does not require advanced document preview.

---

# 19. Task Relationships

Tasks can have simple relationships.

Supported relationship types:

* Blocks
* Blocked by
* Relates to

Example:

```text
TASK-101 blocks TASK-105
```

This allows users to understand basic dependencies between tasks.

---

# 20. Search

Users can search tasks.

Search should support basic text matching, primarily against:

* Task title
* Task ID
* Description

Example:

```text
Search: payment

Results:
TASK-101 Fix payment API
TASK-108 Payment validation
```

---

# 21. Filters

Users can filter tasks by:

* Status
* Assignee
* Priority
* Type
* Labels

Example:

```text
Priority: High
Assignee: John
Type: Bug
```

---

# 22. Board Views

The MVP supports two views.

## Kanban View

Visual columns with draggable cards.

## List View

Tasks displayed in a table/list.

Example:

| ID       | Title      | Type    | Status      | Priority | Assignee |
| -------- | ---------- | ------- | ----------- | -------- | -------- |
| TASK-101 | Fix login  | Bug     | In Progress | High     | John     |
| TASK-102 | Add search | Feature | To Do       | Medium   | Sarah    |

---

# 23. Dashboard

After login, users see a simple dashboard.

The dashboard contains:

## Projects

Projects the user belongs to.

## My Tasks

Tasks assigned to the current user.

## Overdue Tasks

Tasks assigned to the current user that are past their due date.

Example:

```text
Dashboard

My Projects
----------------
Website Redesign
Mobile App
Internal Tools

My Tasks
----------------
TASK-101 Fix login
TASK-105 Add search
TASK-108 Update API

Overdue
----------------
TASK-103 Fix database issue
```

---

# 24. Activity History

The system automatically records important changes.

Examples:

```text
John created TASK-101

Sarah assigned TASK-101 to John

John moved TASK-101
To Do → In Progress

John changed priority
Medium → High

Sarah added label "backend"

John added a comment
```

Activity history is automatically generated by the system.

Users do not manually create activity records.

---

# 25. Project Invitations

Project admins can invite users by email.

Example:

```text
Project: Website Redesign

Invite:
john@example.com

Role:
Member
```

The invited user receives an invitation and can join the project.

---

# 26. Notifications

## MVP decision

No notification system.

Do NOT implement:

* Email notifications
* Push notifications
* In-app notification center
* Notification preferences

These can be added later.

---

# 27. Main Screens

The MVP should contain approximately these screens:

```text
Authentication
├── Login
├── Register
└── Google Login

Application
├── Dashboard
├── Projects
│   └── Project
│       ├── Kanban Board
│       ├── List View
│       ├── Task Details
│       ├── Members
│       └── Settings
└── Profile
```

---

# 28. Core User Flow

## New User

```text
Register
   ↓
Login
   ↓
Dashboard
   ↓
Create Project
   ↓
Create/Configure Board
   ↓
Create Columns
   ↓
Create Tasks
   ↓
Assign Tasks
   ↓
Move Tasks
   ↓
Complete Work
```

---

# 29. Typical Team Flow

```text
Admin creates project
        ↓
Admin invites team members
        ↓
Admin configures board
        ↓
Member creates task
        ↓
Task assigned to developer
        ↓
Developer moves task:
To Do → In Progress
        ↓
Developer adds comment
        ↓
Developer uploads attachment
        ↓
Developer moves task:
In Progress → Review
        ↓
Reviewer checks task
        ↓
Task → Done
```

---

# 30. MVP Database Entities

The initial database should contain approximately:

```text
User
Project
ProjectMember
Board
Column
Task
TaskLabel
Label
Comment
Attachment
TaskRelation
Activity
Invitation
```

Relationships:

```text
User
 ├── ProjectMember
 ├── Task
 ├── Comment
 ├── Attachment
 └── Activity

Project
 ├── ProjectMember
 ├── Board
 ├── Label
 ├── Task
 └── Invitation

Board
 └── Column

Column
 └── Task

Task
 ├── Comment
 ├── Attachment
 ├── Label
 ├── TaskRelation
 └── Activity
```

---

# 31. MVP API Areas

The backend should expose REST APIs for:

```text
Authentication
Users
Projects
Project Members
Invitations
Boards
Columns
Tasks
Comments
Attachments
Labels
Task Relations
Activity
```

Example endpoints:

```text
GET    /api/projects
POST   /api/projects

GET    /api/projects/{id}
PUT    /api/projects/{id}
DELETE /api/projects/{id}

GET    /api/projects/{id}/tasks
POST   /api/projects/{id}/tasks

GET    /api/tasks/{id}
PUT    /api/tasks/{id}
DELETE /api/tasks/{id}

POST   /api/tasks/{id}/comments
GET    /api/tasks/{id}/comments

POST   /api/tasks/{id}/attachments

POST   /api/tasks/{id}/relations
```

Exact API design can be finalized during implementation.

---

# 32. Security Requirements

The application must enforce authorization on the backend.

Important rules:

* Users can only access projects they belong to
* Viewers cannot modify project data
* Members cannot manage project members
* Only admins can manage project configuration
* Users cannot modify another user's comments
* API endpoints must validate permissions
* Authentication must be required for protected resources
* File uploads must be validated

Frontend hiding buttons is NOT sufficient for security.

---

# 33. MVP Out of Scope

The following features are intentionally excluded from MVP:

* Real-time collaboration
* WebSockets
* Notifications
* Email notifications
* Push notifications
* Advanced analytics
* Burndown charts
* Sprint planning
* Scrum boards
* Epics
* Story points
* Time tracking
* Work logs
* Gantt charts
* Calendar view
* Custom permission builder
* Custom task types
* Custom priority systems
* Rich-text comments
* Comment threads
* Reactions
* @mentions
* Advanced Jira Query Language
* Automation rules
* Workflow automation
* AI features
* Mobile native application
* Slack/Teams integration
* GitHub integration
* Microsoft Teams integration

These may become future features.

---

# 34. MVP Definition of Done

The MVP is complete when a user can:

```text
Register
  ↓
Login
  ↓
Create a project
  ↓
Invite another user
  ↓
Create/configure a board
  ↓
Create columns
  ↓
Create a task
  ↓
Assign the task
  ↓
Set type/priority/labels/due date
  ↓
Move the task using drag & drop
  ↓
Open task details
  ↓
Add a comment
  ↓
Upload an attachment
  ↓
Link another task
  ↓
See activity history
  ↓
Search/filter tasks
  ↓
Switch Kanban ↔ List view
  ↓
See assigned/overdue tasks on dashboard
```

If all of the above works reliably, the MVP is finished.

---

# 35. Product Philosophy

Keep the application:

* Simple
* Fast
* Clean
* Responsive
* Easy to understand
* Realistic enough to demonstrate professional development skills

The application should feel like a **small real-world Jira alternative**, while deliberately avoiding the complexity of full Jira.

---

# 36. Scope Freeze

**MVP scope is frozen.**

New features should NOT be added during initial implementation unless they are required to make an existing MVP feature work correctly.

Future ideas should be recorded separately under:

```text
FUTURE-IDEAS.md
```

This prevents scope creep.

---

# 37. Suggested Development Order

Build in this order:

```text
1. Project setup
2. Database
3. Authentication
4. Users & roles
5. Projects
6. Project membership
7. Boards & columns
8. Tasks
9. Kanban drag & drop
10. Task details
11. Comments
12. Labels
13. Attachments
14. Task relationships
15. Activity history
16. Search & filters
17. List view
18. Dashboard
19. Permissions/security
20. Testing
21. CI/CD
22. Deployment
```

---

# 38. Final MVP Summary

The application is a **multi-user, Jira-style project management system** based around Kanban boards.

Core hierarchy:

```text
Users
  ↓
Projects
  ↓
Boards
  ↓
Columns
  ↓
Tasks
```

Core task functionality:

```text
Task
├── Type
├── Priority
├── Status
├── Assignee
├── Labels
├── Due Date
├── Description
├── Comments
├── Attachments
├── Relationships
└── Activity History
```

Core views:

```text
Dashboard
Kanban
List
Task Details
```

Core roles:

```text
Admin
Member
Viewer
```

This is the **official MVP scope** for the Mini Jira Kanban project.
