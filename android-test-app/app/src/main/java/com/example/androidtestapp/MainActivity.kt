package com.example.androidtestapp

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class MainActivity : AppCompatActivity() {

    data class TestCase(
        val title: String,
        val subtitle: String,
        val activity: Class<out Activity>,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val cases = listOf(
            TestCase("Controls", "Inputs, toggles, spinner", ControlsActivity::class.java),
            TestCase("Lists", "RecyclerView scrolling and selection", ListActivity::class.java),
            TestCase("Dialogs", "Alert, bottom sheet, pickers", DialogActivity::class.java),
            TestCase("Gestures", "Tap, double tap, long press", GesturesActivity::class.java),
            TestCase("Permissions", "Runtime permission flow", PermissionActivity::class.java),
            TestCase("WebView", "Local HTML and JS", WebViewActivity::class.java),
            TestCase("Scrolling", "Long scroll content", ScrollActivity::class.java),
            TestCase("Tabs", "TabLayout with ViewPager2", TabsActivity::class.java),
            TestCase("Notifications", "Post a system notification", NotificationsActivity::class.java),
            TestCase("File Picker", "OpenDocument activity result", FilePickerActivity::class.java),
            TestCase("Snackbars & Toasts", "Transient feedback UI", SnackbarToastActivity::class.java),
            TestCase("Bottom Navigation", "Bottom nav with fragments", BottomNavActivity::class.java),
            TestCase("Sliders", "SeekBar, rating, progress", SliderActivity::class.java),
            TestCase("Swipe Refresh", "Pull-to-refresh behavior", SwipeRefreshActivity::class.java),
            TestCase("Counter", "Increment/decrement controls", CounterActivity::class.java),
            TestCase("App Bar & Menu", "Toolbar menu actions", AppBarMenuActivity::class.java),
            TestCase("Navigation Drawer", "DrawerLayout and navigation view", NavigationDrawerActivity::class.java),
            TestCase("Swipe List", "Swipe-to-delete list rows", SwipeListActivity::class.java),
            TestCase("Chips", "Filter chip selection", ChipsActivity::class.java),
        )

        val recyclerView = findViewById<RecyclerView>(R.id.case_list)
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = TestCaseAdapter(cases) { testCase ->
            startActivity(Intent(this, testCase.activity))
        }
    }
}

private class TestCaseAdapter(
    private val cases: List<MainActivity.TestCase>,
    private val onClick: (MainActivity.TestCase) -> Unit,
) : RecyclerView.Adapter<TestCaseViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): TestCaseViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_test_case, parent, false)
        return TestCaseViewHolder(view, onClick)
    }

    override fun onBindViewHolder(holder: TestCaseViewHolder, position: Int) {
        holder.bind(cases[position])
    }

    override fun getItemCount(): Int = cases.size
}

private class TestCaseViewHolder(
    itemView: View,
    private val onClick: (MainActivity.TestCase) -> Unit,
) : RecyclerView.ViewHolder(itemView) {

    private val titleView: TextView = itemView.findViewById(R.id.case_title)
    private val subtitleView: TextView = itemView.findViewById(R.id.case_subtitle)
    private var current: MainActivity.TestCase? = null

    init {
        itemView.setOnClickListener {
            current?.let(onClick)
        }
    }

    fun bind(testCase: MainActivity.TestCase) {
        current = testCase
        titleView.text = testCase.title
        subtitleView.text = testCase.subtitle
    }
}
