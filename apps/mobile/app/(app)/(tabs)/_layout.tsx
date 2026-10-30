import {
  PAGES_WITHOUT_TAB,
  pageWithoutTabOptions,
  TAB_BAR_HEIGHT,
  TabBarSpaceProvider,
  TABS,
  tabIcon,
  tabScreenOptions,
} from "@gamedaygo/ui";
import { Tabs } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

// Bottom tabs: Home, Schedule, Plan, My Game Days, kept on every page after onboarding,
// including game detail, Settings and Inbox (UI/UX §2.2). Back follows the visit history.
// The bar floats over the page's photo, so pages leave room for it.
export default function TabsLayout() {
  const { bottom } = useSafeAreaInsets();
  return (
    <TabBarSpaceProvider value={TAB_BAR_HEIGHT + bottom}>
      <Tabs screenOptions={tabScreenOptions({ bottomInset: bottom })} backBehavior="history">
        {TABS.map((tab) => (
          <Tabs.Screen
            key={tab.name}
            name={tab.name}
            options={{ title: tab.title, tabBarIcon: tabIcon(tab.icon) }}
          />
        ))}
        {PAGES_WITHOUT_TAB.map((name) => (
          <Tabs.Screen key={name} name={name} options={pageWithoutTabOptions} />
        ))}
      </Tabs>
    </TabBarSpaceProvider>
  );
}
