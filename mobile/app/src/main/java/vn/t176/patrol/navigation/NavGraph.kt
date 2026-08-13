package vn.t176.patrol.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import vn.t176.patrol.data.AppContainer
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.UserSession
import vn.t176.patrol.ui.alerts.AlertsScreen
import vn.t176.patrol.ui.alerts.AlertsViewModel
import vn.t176.patrol.ui.audit.AuditScreen
import vn.t176.patrol.ui.audit.AuditViewModel
import vn.t176.patrol.ui.detail.DetailScreen
import vn.t176.patrol.ui.detail.DetailViewModel
import vn.t176.patrol.ui.login.LoginScreen

object Routes {
    const val LOGIN = "login"
    const val ALERTS = "alerts"
    const val AUDIT = "audit"
    const val DETAIL = "detail/{eventId}"

    fun detail(eventId: String) = "detail/$eventId"
}

@Composable
fun PatrolNavGraph(
    container: AppContainer,
    session: UserSession?,
    onSignedIn: (UserSession) -> Unit,
    onSignedOut: () -> Unit,
    navController: NavHostController = rememberNavController(),
) {
    NavHost(
        navController = navController,
        startDestination = if (session == null) Routes.LOGIN else Routes.ALERTS,
    ) {
        composable(Routes.LOGIN) {
            LoginScreen(onSignedIn = onSignedIn)
        }

        composable(Routes.ALERTS) {
            val role = session?.role ?: return@composable
            val vm: AlertsViewModel = viewModel(
                factory = viewModelFactory {
                    initializer { AlertsViewModel(container.eventRepository) }
                },
            )
            AlertsScreen(
                viewModel = vm,
                role = role,
                onOpenEvent = { navController.navigate(Routes.detail(it)) },
                onOpenAudit = { navController.navigate(Routes.AUDIT) },
                onLogout = onSignedOut,
            )
        }

        composable(
            route = Routes.DETAIL,
            arguments = listOf(navArgument("eventId") { type = NavType.StringType }),
            // Thông báo mở thẳng vào đây; nếu chưa đăng nhập thì màn này tự
            // thoát ra và người dùng quay về đăng nhập.
            deepLinks = listOf(navDeepLink { uriPattern = "app://event/{eventId}" }),
        ) { entry ->
            val currentUser = session ?: return@composable
            val eventId = entry.arguments?.getString("eventId").orEmpty()

            val vm: DetailViewModel = viewModel(
                key = eventId,
                factory = viewModelFactory {
                    initializer {
                        DetailViewModel(
                            eventRepository = container.eventRepository,
                            actionRepository = container.actionRepository,
                            eventId = eventId,
                            actorName = currentUser.displayName,
                        )
                    }
                },
            )
            DetailScreen(
                viewModel = vm,
                role = currentUser.role,
                onBack = {
                    if (!navController.popBackStack()) {
                        navController.navigate(Routes.ALERTS)
                    }
                },
            )
        }

        composable(Routes.AUDIT) {
            // Audit chỉ dành cho Quản lý — chặn cả khi điều hướng thẳng bằng route.
            if (session?.role != Role.MANAGER) return@composable

            val vm: AuditViewModel = viewModel(
                factory = viewModelFactory {
                    initializer { AuditViewModel(container.auditRepository) }
                },
            )
            AuditScreen(viewModel = vm, onBack = { navController.popBackStack() })
        }
    }
}
