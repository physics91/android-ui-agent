package com.example.androidtestapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.viewpager2.adapter.FragmentStateAdapter
import androidx.viewpager2.widget.ViewPager2
import com.google.android.material.tabs.TabLayout
import com.google.android.material.tabs.TabLayoutMediator

class TabsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_tabs)

        val tabLayout = findViewById<TabLayout>(R.id.tab_layout)
        val viewPager = findViewById<ViewPager2>(R.id.view_pager)

        val titles = listOf("Tab A", "Tab B", "Tab C")
        viewPager.adapter = TabsAdapter(this, titles)

        TabLayoutMediator(tabLayout, viewPager) { tab, position ->
            tab.text = titles[position]
            tab.contentDescription = titles[position]
        }.attach()
    }
}

private class TabsAdapter(
    activity: AppCompatActivity,
    private val titles: List<String>,
) : FragmentStateAdapter(activity) {

    override fun getItemCount(): Int = titles.size

    override fun createFragment(position: Int): Fragment {
        return SimpleTextFragment.newInstance("${titles[position]} Content")
    }
}
