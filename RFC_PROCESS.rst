===========
RFC Process
===========

Major changes to FlameIQ require a formal RFC (Request for Comments)
before implementation begins.

When is an RFC required?
=========================

Required:

* Schema changes (``schema/v1/`` is immutable; new fields need RFC)
* New statistical algorithms or changes to existing ones
* New baseline strategies
* CLI exit code changes
* Breaking public Python API changes
* New top-level CLI commands

Not required:

* Bug fixes
* Documentation improvements
* New providers (PR with checklist is sufficient)
* Dependency updates
* Performance improvements with no observable behaviour change

RFC lifecycle
=============

1. **Draft** — Open a GitHub Discussion with ``[RFC]`` prefix
2. **Discussion** — Community feedback, 7-day minimum comment period
3. **Revised** — Incorporate feedback, mark as ready for vote
4. **Vote** — Maintainers vote. Requires two-thirds majority.
5. **Accepted** — RFC merged to ``docs/rfcs/``. Implementation begins.
6. **Final** — Implementation shipped and documented.

Template
========

::

    RFC-NNNN: <Title>
    ==================

    :Author:  <name>
    :Status:  Draft
    :Created: YYYY-MM-DD

    Motivation
    ----------

    Why is this change needed?

    Proposed Change
    ---------------

    Precise description.

    Mathematical Specification
    --------------------------

    (Required for algorithm changes.)

    Backward Compatibility
    ----------------------

    What breaks? Migration guide?

    Alternatives Considered
    -----------------------

    What else was evaluated?

    Test Plan
    ---------

    How will correctness be verified?
