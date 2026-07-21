import type { QueryClient } from "@tanstack/react-query";

import { dashboardKeys } from "@/hooks/useDashboard";
import { jobKeys } from "@/hooks/useExecutions";
import { findingKeys } from "@/hooks/useFindings";
import { hostInventoryKeys } from "@/hooks/useHostInventory";

/**
 * Invalidate every cross-assessment aggregate view after a deletion that
 * removes hosts/services/technologies/observations/findings out from under
 * it -- deleting an Assessment or one of its Targets, neither of which has
 * a query key of its own scoped narrowly enough to invalidate instead.
 * Without this, the Dashboard/Findings/Hosts/Search pages keep showing the
 * deleted data until the user manually refreshes.
 */
export function invalidateInventoryViews(queryClient: QueryClient): void {
  queryClient.invalidateQueries({ queryKey: dashboardKeys.all });
  queryClient.invalidateQueries({ queryKey: hostInventoryKeys.all });
  queryClient.invalidateQueries({ queryKey: findingKeys.all });
  queryClient.invalidateQueries({ queryKey: jobKeys.all });
}
