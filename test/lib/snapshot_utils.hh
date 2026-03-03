
/*
 * Copyright (C) 2026-present ScyllaDB
 */

/*
 * SPDX-License-Identifier: LicenseRef-ScyllaDB-Source-Available-1.0
 */

#pragma once

#include "db/snapshot-ctl.hh"
#include "db/config.hh"
#include "test/lib/cql_test_env.hh"
#include "test/lib/random_utils.hh"
#include "test/lib/tmpdir.hh"
#include "test/lib/log.hh"
#include "db/view/view_builder.hh"


// Snapshot tests and their helpers
// \param func: function to be called back, in a seastar thread.
future<> do_with_some_data_in_thread(std::vector<sstring> cf_names, std::function<void (cql_test_env&)> func, bool create_mvs = false, shared_ptr<db::config> db_cfg_ptr = {}, size_t num_keys = 2);

future<> take_snapshot(cql_test_env& e, sstring ks_name = "ks", sstring cf_name = "cf", sstring snapshot_name = "test", db::snapshot_options opts = {});
